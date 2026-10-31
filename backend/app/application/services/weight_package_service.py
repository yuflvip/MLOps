import configparser
from datetime import datetime, timezone, timedelta
import ftplib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shlex
import shutil
import tarfile
import tempfile
from uuid import uuid4

from sqlalchemy import select, func, or_
from app.domain.common.exceptions import ExpValidationError, ExpConflictError, ExpNotFoundError
from app.domain.common.packaging import ProjectPackagingConfig
from app.domain.common.experiment_metadata import read_experiment_metadata
from app.infrastructure.db.models import ExpModel, ProjectModel, ModelConversionModel, WeightPackageModel
from app.infrastructure.package_lock import package_lock
from app.infrastructure.onnx_metadata import inspect_onnx
from app.application.services.exp_service import ExpService

PLATFORMS = {"x86": (".onnx", "x86"), "3403": (".om", None), "692": (".bin", "692"),
             "530": (".bin", "530"), "3588": (".rknn", "rk3588")}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_name(value):
    if not value or len(value) > 128 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ExpValidationError("模型族标识和模型框架仅支持字母、数字、下划线及连字符")
    return value


def serialize(item):
    result = {key: getattr(item, key) for key in ("id", "package_name", "project_id", "exp_id", "project_key", "exp_name", "platform", "runtime", "model_framework", "model_size", "model_type", "training_date", "source_file", "local_path", "unpacked_path", "size_bytes", "sha256", "ftp_uploaded", "ftp_path", "upload_status", "upload_error")}
    for key in ("created_at", "updated_at", "ftp_uploaded_at", "training_finished_at"):
        value = getattr(item, key)
        result[key] = value.replace(tzinfo=timezone.utc).isoformat() if value and value.tzinfo is None else value.isoformat() if value else None
    return result


class WeightPackageService:
    def __init__(self, session, settings, storage_root):
        self.session = session
        self.settings = settings
        self.root = Path(storage_root).resolve()

    def _within(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(self.root):
            raise ExpValidationError("打包文件路径超出配置存储目录")
        return path

    def _record(self, id):
        record = self.session.get(WeightPackageModel, id)
        if record is None:
            raise ExpNotFoundError("权重包不存在")
        return record

    def _lock(self, name):
        return package_lock(self._within(self.root / ".locks" / (hashlib.sha256(name.encode()).hexdigest() + ".lock")))

    def _prepare(self, exp_id, source_file, platform, runtime=None, package_name=None):
        exp = self.session.get(ExpModel, exp_id)
        if exp is None:
            raise ExpNotFoundError("实验不存在")
        project = self.session.get(ProjectModel, exp.project_id)
        if project is None:
            raise ExpNotFoundError("模型族不存在")
        if platform not in PLATFORMS:
            raise ExpValidationError("不支持的端侧平台")
        root = Path(exp.resolved_path).resolve()
        source = (root / source_file).resolve()
        if not source_file or Path(source_file).is_absolute() or not source.is_relative_to(root) or not source.is_file():
            raise ExpValidationError("所选模型文件不存在或不在实验目录内")
        if source.stat().st_size == 0 or source.suffix.lower() != PLATFORMS[platform][0]:
            raise ExpValidationError("模型文件为空或格式与平台不匹配")
        conversions = list(self.session.scalars(select(ModelConversionModel).where(ModelConversionModel.exp_id == exp_id).order_by(ModelConversionModel.id.desc())))
        matching = [item for item in conversions if source_file.replace("\\", "/") in ([item.output_file] + json.loads(item.result_files_json or "[]"))]
        conversion = matching[0] if matching else None
        if conversion and conversion.status != "succeeded":
            raise ExpValidationError("所选文件的最新转换任务尚未成功")
        if platform == "3403":
            inferred = {"onnx_to_hisi3403": "3403svp", "onnx_to_hisi3403_ascend_nnn": "3403nnn"}.get(conversion.converter_code if conversion else "")
            if runtime and inferred and runtime != inferred:
                raise ExpValidationError("3403 运行时与转换记录不匹配")
            runtime = inferred or runtime
            if runtime not in {"3403svp", "3403nnn"}:
                raise ExpValidationError("请选择3403模型运行时：SVP或NNN")
        else:
            runtime = PLATFORMS[platform][1]
        metadata = read_experiment_metadata(root)
        framework = exp.model_framework or metadata["model_framework"]
        if not framework:
            raise ExpValidationError("实验缺少模型框架，请补充模型框架或训练配置")
        framework = safe_name(framework)
        family = safe_name(project.project)
        first, separator, rest = family.partition("_")
        package_key = first + separator + rest.replace("_", "")
        results_path = root / "results.png"
        if not results_path.is_file():
            raise ExpValidationError("缺少训练结束时间（results.png），无法生成包名日期")
        finished = ExpService(exp_repository=None, project_repository=None)._file_timestamp(results_path)
        date = finished.astimezone(timezone(timedelta(hours=8))).strftime("%Y%m%d")
        bundle = "weight_%s_%s_%s_%s" % (package_key, framework, platform, date)
        default_package_name = bundle + ".tgz"
        if package_name and package_name.strip():
            custom = package_name.strip()
            if not custom.endswith(".tgz"):
                custom += ".tgz"
            if ".." in custom or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.tgz", custom):
                raise ExpValidationError("包名称仅支持字母、数字、下划线、点和连字符，不能包含路径或 ..")
            bundle = custom[:-4]
        if len(bundle) > 240:
            raise ExpValidationError("包名称过长，请缩短模型族标识")
        values = json.loads(project.packaging_json or "{}")
        values["cfg_filename"] = family + ".cfg"
        values["names_filename"] = family + ".names"
        config = ProjectPackagingConfig.model_validate(values)
        model_link = config.model_links.get(runtime)
        if not model_link or not config.cfg_link or not config.names_link:
            raise ExpValidationError("模型族的软链接名称尚未配置完整")
        if not config.cfg_content.strip() or not config.names_content.strip():
            raise ExpValidationError("模型族 cfg/names 内容不能为空")
        parser = configparser.ConfigParser()
        try:
            parser.read_string(config.cfg_content)
            count = parser.getint("yolo", "class_num")
            width = parser.getint("yolo", "in_width")
            height = parser.getint("yolo", "in_height")
        except (configparser.Error, ValueError) as exc:
            raise ExpValidationError("cfg 需包含 [yolo] 的 class_num、in_width、in_height") from exc
        names = config.names_content.splitlines()
        if any(not name.strip() for name in names) or count != len(names) or count <= 0 or width <= 0 or height <= 0:
            raise ExpValidationError("cfg类别数与names不一致、names有空行或输入尺寸无效")
        # Verify known training class order without unpickling checkpoint files.
        args_path = root / "args.json"
        if args_path.is_file() and args_path.stat().st_size <= 1024 * 1024:
            try:
                args = json.loads(args_path.read_text(encoding="utf-8-sig"))
                classes = args.get("dataset_layout", {}).get("class_names")
            except (ValueError, AttributeError):
                classes = None
            if classes is not None and classes != names:
                raise ExpValidationError("names与训练配置的类别或顺序不一致")
        size = exp.model_size or metadata["model_size"]
        if size and size not in {"%d×%d" % (width, height), "%dx%d" % (width, height)}:
            raise ExpValidationError("cfg输入尺寸与实验输入尺寸不一致")
        model_stem = bundle.removeprefix("weight_")
        if not model_stem:
            raise ExpValidationError("包名称去掉 weight_ 和 .tgz 后不能为空")
        model_filename = model_stem + source.suffix.lower()
        files = {model_filename: source}
        if platform == "x86":
            try:
                metadata_onnx = inspect_onnx(source)
                dimensions = metadata_onnx["input_dimensions"]
                if len(dimensions) == 4 and dimensions[1] in (1, 3, 4):
                    if (dimensions[2] > 0 and dimensions[2] != height) or (dimensions[3] > 0 and dimensions[3] != width):
                        raise ExpValidationError("ONNX实际输入尺寸与cfg不一致")
                for location in metadata_onnx["external_files"]:
                    relative = PurePosixPath(location)
                    path = (source.parent / location).resolve()
                    if not location or relative.is_absolute() or ".." in relative.parts or "\\" in location or not path.is_relative_to(root) or not path.is_file():
                        raise ExpValidationError("ONNX外部权重路径无效或文件缺失")
                    if location in {model_filename, config.cfg_filename, config.names_filename, "mklink.sh"}:
                        raise ExpValidationError("ONNX外部权重与包内文件名冲突")
                    files[location] = path
            except ExpValidationError:
                raise
            except Exception as exc:
                raise ExpValidationError("无法读取所选ONNX文件") from exc
        links = {model_link: model_filename, config.cfg_link: config.cfg_filename, config.names_link: config.names_filename}
        lines = ["#!/bin/sh", "set -eu", "cd " + shlex.quote(self.settings.deploy_dir)]
        for link, filename in links.items():
            target = bundle + "/" + filename
            lines += ["test -f " + shlex.quote(target)]
        for link, filename in links.items():
            lines += ["ln -sfn " + shlex.quote(bundle + "/" + filename) + " " + shlex.quote(link)]
        script = "\n".join(lines) + "\n"
        snapshot = {"project_id": project.id, "exp_id": exp.id, "project_key": family, "exp_name": exp.name,
                    "platform": platform, "runtime": runtime, "model_framework": framework, "model_size": size or "%d×%d" % (width, height),
                    "model_type": project.model_type, "training_finished_at": finished.isoformat(),
                    "training_date": date, "source_file": source_file, "package_name": bundle + ".tgz",
                    "default_package_name": default_package_name, "config": config.model_dump(), "script": script, "deploy_dir": self.settings.deploy_dir,
                    "sources": {name: {"size": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns} for name, path in files.items()}}
        token = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
        return snapshot, token, files

    def preview(self, exp_id, source_file, platform, runtime=None, package_name=None):
        snapshot, token, files = self._prepare(exp_id, source_file, platform, runtime, package_name)
        destination = self._within(self.root / snapshot["project_key"] / snapshot["package_name"])
        exists = self.session.scalar(select(WeightPackageModel.id).where(WeightPackageModel.package_name == snapshot["package_name"])) is not None or destination.exists() or destination.with_suffix("").exists()
        return {"package_name": snapshot["package_name"], "default_package_name": snapshot["default_package_name"], "platform": platform, "runtime": snapshot["runtime"],
                "local_path": str(destination), "unpacked_path": str(destination.with_suffix("")), "exists": exists,
                "preview_token": token, "cfg_content": snapshot["config"]["cfg_content"], "names_content": snapshot["config"]["names_content"],
                "script": snapshot["script"], "files": list(files) + [snapshot["config"]["cfg_filename"], snapshot["config"]["names_filename"], "mklink.sh"], "links": snapshot["config"]["model_links"]}

    def create(self, exp_id, source_file, platform, runtime=None, overwrite=False, preview_token=None, package_name=None):
        snapshot, token, files = self._prepare(exp_id, source_file, platform, runtime, package_name)
        if preview_token != token:
            raise ExpConflictError("模型或配置已变化，请重新预览后打包")
        with self._lock(snapshot["package_name"]):
            record = self.session.scalar(select(WeightPackageModel).where(WeightPackageModel.package_name == snapshot["package_name"]))
            if record and record.project_id != snapshot["project_id"]:
                raise ExpConflictError("规范化后的包名与其他模型族冲突，请修改模型族标识")
            family_dir = self._within(self.root / snapshot["project_key"])
            family_dir.mkdir(parents=True, exist_ok=True)
            archive = self._within(family_dir / snapshot["package_name"])
            unpacked = self._within(archive.with_suffix(""))
            if (record or archive.exists() or unpacked.exists()) and not overwrite:
                raise ExpConflictError("已存在该包名，请选择覆盖或取消")
            with tempfile.TemporaryDirectory(prefix=".build-", dir=family_dir) as temp:
                stage = Path(temp)
                content = stage / unpacked.name
                content.mkdir()
                for name, source in files.items():
                    target = content / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    stat = source.stat()
                    if {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns} != snapshot["sources"][name]:
                        raise ExpConflictError("打包过程中源模型发生变化，请重新打包")
                config = snapshot["config"]
                for name, text in ((config["cfg_filename"], config["cfg_content"]), (config["names_filename"], config["names_content"]), ("mklink.sh", snapshot["script"])):
                    (content / name).write_text(text, encoding="utf-8", newline="\n")
                (content / "mklink.sh").chmod(0o755)
                temporary_archive = stage / archive.name
                def permissions(info):
                    info.mode = 0o755 if info.isdir() or info.name.endswith("/mklink.sh") else 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    return info
                with tarfile.open(temporary_archive, "w:gz") as tar:
                    tar.add(content, arcname=unpacked.name, filter=permissions)
                snapshot["source_sha256"] = {name: sha256(content / name) for name in files}
                digest, archive_size = sha256(temporary_archive), temporary_archive.stat().st_size
                old_dir, old_archive = stage / "previous-directory", stage / "previous.tgz"
                moved_dir = moved_archive = new_dir = new_archive = False
                try:
                    if unpacked.exists():
                        unpacked.rename(old_dir); moved_dir = True
                    if archive.exists():
                        archive.rename(old_archive); moved_archive = True
                    content.rename(unpacked); new_dir = True
                    temporary_archive.rename(archive); new_archive = True
                    if record is None:
                        record = WeightPackageModel()
                        self.session.add(record)
                    for key in ("package_name", "project_id", "exp_id", "project_key", "exp_name", "platform", "runtime", "model_framework", "model_size", "model_type", "training_date", "source_file"):
                        setattr(record, key, snapshot[key])
                    record.training_finished_at = datetime.fromisoformat(snapshot["training_finished_at"])
                    record.local_path, record.unpacked_path = str(archive), str(unpacked)
                    record.size_bytes, record.sha256 = archive_size, digest
                    record.snapshot_json = json.dumps(snapshot, ensure_ascii=False)
                    record.ftp_uploaded = False
                    record.ftp_path = record.ftp_uploaded_at = record.upload_error = None
                    record.upload_status = "pending"
                    record.created_at = datetime.now(timezone.utc)
                    record.updated_at = record.created_at
                    self.session.flush()
                    built = serialize(record)
                    self.session.commit()
                except Exception:
                    self.session.rollback()
                    if new_dir: unpacked.rename(stage / "failed-directory")
                    if new_archive: archive.rename(stage / "failed.tgz")
                    if moved_dir: old_dir.rename(unpacked)
                    if moved_archive: old_archive.rename(archive)
                    raise
            return built

    def list(self, page=1, page_size=20, keyword=None, platform=None, uploaded=None, model_type=None, project_id=None, upload_status=None):
        conditions = []
        if keyword:
            conditions.append(or_(*[column.icontains(keyword, autoescape=True) for column in (WeightPackageModel.project_key, WeightPackageModel.package_name, WeightPackageModel.exp_name)]))
        if model_type: conditions.append(WeightPackageModel.model_type == model_type)
        if project_id is not None: conditions.append(WeightPackageModel.project_id == project_id)
        if upload_status:
            if upload_status not in {"pending", "uploading", "succeeded", "failed"}:
                raise ExpValidationError("上传状态无效")
            conditions.append(WeightPackageModel.upload_status == upload_status)
        if platform: conditions.append(WeightPackageModel.platform == platform)
        if uploaded is not None: conditions.append(WeightPackageModel.ftp_uploaded == uploaded)
        rows = self.session.scalars(select(WeightPackageModel).where(*conditions).order_by(WeightPackageModel.created_at.desc(), WeightPackageModel.id.desc()).offset((page-1)*page_size).limit(page_size))
        total = self.session.scalar(select(func.count()).select_from(WeightPackageModel).where(*conditions))
        return {"items": [serialize(row) for row in rows], "total": total, "page": page, "page_size": page_size}

    def download(self, id):
        record = self._record(id)
        path = self._within(record.local_path)
        if not path.is_file(): raise ExpNotFoundError("本地压缩包不存在")
        return path, record.package_name

    def upload(self, id, overwrite=False):
        record = self._record(id)
        settings = self.settings.ftp
        if not settings.enabled or not settings.host or not settings.username:
            raise ExpValidationError("请先在配置文件中启用并配置FTP服务器")
        password = os.environ.get(settings.password_env, "") or settings.password.get_secret_value()
        if not password: raise ExpValidationError("FTP密码未配置")
        if not settings.remote_dir.startswith("/") or ".." in PurePosixPath(settings.remote_dir).parts:
            raise ExpValidationError("FTP远端根目录必须是绝对路径且不包含 ..")
        with self._lock(record.package_name):
            self.session.refresh(record)
            path, _ = self.download(id)
            if sha256(path) != record.sha256:
                raise ExpValidationError("本地压缩包哈希与打包记录不一致，请重新打包")
            remote_path = posixpath.join(settings.remote_dir, record.project_key, record.package_name)
            ftp = ftplib.FTP_TLS() if settings.tls else ftplib.FTP()
            temporary = "." + record.package_name + "." + uuid4().hex + ".part"
            record.upload_status = "uploading"
            record.upload_error = None
            self.session.commit()
            connected = False
            try:
                ftp.connect(settings.host, settings.port, timeout=settings.timeout_seconds)
                ftp.login(settings.username, password)
                connected = True
                if settings.tls: ftp.prot_p()
                ftp.set_pasv(settings.passive)
                ftp.cwd("/")
                for part in PurePosixPath(posixpath.dirname(remote_path)).parts:
                    if part == "/": continue
                    try: ftp.cwd(part)
                    except ftplib.error_perm:
                        ftp.mkd(part)
                        ftp.cwd(part)
                existing = record.package_name in [posixpath.basename(name) for name in ftp.nlst()]
                if existing and not overwrite:
                    raise ExpConflictError("FTP已存在同名文件，请选择覆盖或取消")
                with path.open("rb") as handle:
                    ftp.storbinary("STOR " + temporary, handle, blocksize=1024*1024)
                ftp.voidcmd("TYPE I")
                remote_size = ftp.size(temporary)
                if remote_size != path.stat().st_size:
                    raise ExpValidationError("FTP文件大小校验失败")
                # Some FTP servers cannot rename over an existing destination.
                old_remote = "." + record.package_name + "." + uuid4().hex + ".previous"
                renamed_old = False
                if existing:
                    ftp.rename(record.package_name, old_remote)
                    renamed_old = True
                try:
                    ftp.rename(temporary, record.package_name)
                except Exception:
                    if renamed_old: ftp.rename(old_remote, record.package_name)
                    raise
                if renamed_old:
                    try: ftp.delete(old_remote)
                    except ftplib.all_errors: pass
                record.ftp_uploaded = True
                record.ftp_path = remote_path
                record.ftp_uploaded_at = datetime.now(timezone.utc)
                record.upload_status = "succeeded"
                self.session.commit()
                return serialize(record)
            except Exception as exc:
                if connected:
                    try: ftp.delete(temporary)
                    except ftplib.all_errors: pass
                self.session.rollback()
                self.session.refresh(record)
                record.upload_status = "failed"
                # Never persist FTP server replies: they can contain credentials.
                record.upload_error = str(exc) if isinstance(exc, (ExpValidationError, ExpConflictError)) else "FTP上传失败，请检查连接、权限和服务器状态后重试"
                self.session.commit()
                if isinstance(exc, (ExpValidationError, ExpConflictError)): raise
                raise ExpValidationError(record.upload_error) from exc
            finally:
                try: ftp.close()
                except ftplib.all_errors: pass
