import json
from datetime import datetime, timezone
from pathlib import Path
import tarfile
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.infrastructure.db import Base
from app.infrastructure.db.models import ExpModel, ProjectModel, WeightPackageModel
from app.infrastructure.config.settings import ModelPackagingSettings
from app.application.services.exp_service import ExpService
from app.application.services.weight_package_service import WeightPackageService, sha256
from app.domain.common.exceptions import ExpConflictError, ExpValidationError


@pytest.fixture
def setup_package(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    root = tmp_path / "experiment"
    root.mkdir()
    (root / "results.png").write_bytes(b"results")
    (root / "best.om").write_bytes(b"valid-model-content")
    (root / "args.json").write_text(json.dumps({"dataset_layout": {"class_names": ["car", "bus"]}}))
    monkeypatch.setattr(ExpService, "_file_timestamp", lambda self, path: datetime(2026, 10, 30, 18, 2, 3, tzinfo=timezone.utc))
    config = {"model_links": {"3403nnn": "twowheel.weights", "3403svp": "twowheel.weights", "x86": "twowheel.weights", "692": "twowheel.bin"},
        "cfg_link": "twowheel.cfg", "names_link": "twowheel.names", "cfg_content": "[yolo]\nclass_num=2\nin_width=224\nin_height=224\n", "names_content": "car\nbus\n"}
    session = Session(engine)
    project = ProjectModel(project="classify_two_wheel", name="Twowheel", model_type="classification", dataset_ids_json="[]", packaging_json=json.dumps(config))
    session.add(project); session.flush()
    exp = ExpModel(project_id=project.id, name="training-b3", relative_path=root.name, resolved_path=str(root), review_status="pending_review", model_framework="hgnetv2b3", model_size="224×224")
    session.add(exp); session.commit()
    settings = ModelPackagingSettings()
    service = WeightPackageService(session, settings, tmp_path / "packages")
    payload = dict(exp_id=exp.id, source_file="best.om", platform="3403", runtime="3403nnn")
    yield service, payload, root, project
    session.close()


def build(service, payload, **kwargs):
    preview = service.preview(**payload)
    return service.create(**payload, preview_token=preview["preview_token"], **kwargs)


def test_archive_naming_permissions_script_and_query(setup_package):
    service, payload, root, project = setup_package
    preview = service.preview(**payload)
    assert preview["package_name"] == "weight_classify_twowheel_hgnetv2b3_3403_20261031.tgz"
    item = build(service, payload)
    assert Path(item["local_path"]).is_file()
    assert Path(item["unpacked_path"]).parent.name == "classify_two_wheel"
    with tarfile.open(item["local_path"]) as tar:
        script = tar.getmember(Path(item["unpacked_path"]).name + "/mklink.sh")
        assert script.mode == 0o755
        text = tar.extractfile(script).read().decode()
        assert "test -f " in text
        assert "if [ -e " not in text
        assert "拒绝覆盖" not in text
        assert "ln -sfn " in text
        assert "cd /opt/AII/YoloModel" in text
        assert "classify_twowheel_hgnetv2b3_3403_20261031.om twowheel.weights" in text
        assert "\r" not in text
        assert tar.getmember(Path(item["unpacked_path"]).name + "/classify_two_wheel.names").mode == 0o644
    assert service.list(keyword="twowheel", uploaded=False)["total"] == 1
    assert service.list(platform="x86")["total"] == 0
    assert service.download(item["id"])[0].name == item["package_name"]


def test_overwrite_confirmation_and_ftp_reset(setup_package):
    service, payload, root, _ = setup_package
    first = build(service, payload)
    record = service.session.get(WeightPackageModel, first["id"])
    record.ftp_uploaded = True; record.ftp_path = "/old"; service.session.commit()
    with pytest.raises(ExpConflictError, match="已存在"):
        build(service, payload)
    (root / "best.om").write_bytes(b"new model")
    second = build(service, payload, overwrite=True)
    assert second["id"] == first["id"]
    assert second["sha256"] != first["sha256"]
    assert not second["ftp_uploaded"] and second["ftp_path"] is None


def test_stale_preview_and_invalid_sources(setup_package):
    service, payload, root, project = setup_package
    preview = service.preview(**payload)
    (root / "best.om").write_bytes(b"changed")
    with pytest.raises(ExpConflictError, match="重新预览"):
        service.create(**payload, preview_token=preview["preview_token"])
    with pytest.raises(ExpValidationError):
        service.preview(**{**payload, "source_file": "../missing.om"})
    values=json.loads(project.packaging_json); values["names_content"]="bus\ncar\n"
    project.packaging_json=json.dumps(values);service.session.commit()
    with pytest.raises(ExpValidationError, match="顺序"):
        service.preview(**payload)


def test_atomic_restore_when_database_commit_fails(setup_package, monkeypatch):
    service, payload, root, _ = setup_package
    first = build(service, payload)
    original = Path(first["local_path"]).read_bytes()
    (root / "best.om").write_bytes(b"new-content")
    preview=service.preview(**payload)
    monkeypatch.setattr(service.session, "commit", Mock(side_effect=RuntimeError("database failure")))
    with pytest.raises(RuntimeError):
        service.create(**payload, preview_token=preview["preview_token"], overwrite=True)
    assert Path(first["local_path"]).read_bytes() == original
    assert (Path(first["unpacked_path"]) / (first["package_name"].removeprefix("weight_")[:-4] + ".om")).read_bytes() == b"valid-model-content"


def test_onnx_external_weights_are_included(setup_package):
    service, payload, root, _ = setup_package
    def varint(number):
        output = bytearray()
        while number > 127:
            output.append((number & 127) | 128); number >>= 7
        output.append(number)
        return bytes(output)
    def message(number, content):
        return varint(number * 8 + 2) + varint(len(content)) + content
    # Minimal ONNX TensorProto with an external initializer, encoded according
    # to the official protobuf schema. No ONNX runtime is needed for packing.
    entry = message(1, b"location") + message(2, b"weights.data")
    tensor = b"\x08\x04\x10\x01" + message(8, b"weight") + message(13, entry) + b"\x70\x01"
    graph = message(2, b"test") + message(5, tensor)
    (root / "best.onnx").write_bytes(b"\x08\x0a" + message(7, graph))
    (root / "weights.data").write_bytes(b"external tensor data")
    item=build(service, {**payload, "platform":"x86", "source_file":"best.onnx", "runtime":None})
    assert (Path(item["unpacked_path"])/"weights.data").read_bytes()==(root/"weights.data").read_bytes()


class FakeFTP:
    def __init__(self): self.files={};self.commands=[]
    def connect(self,*args,**kwargs): pass
    def login(self,*args): pass
    def cwd(self,*args): pass
    def mkd(self,*args): pass
    def set_pasv(self,*args): pass
    def nlst(self): return list(self.files)
    def storbinary(self,command,handle,**kwargs): self.files[command[5:]]=handle.read()
    def voidcmd(self,*args): pass
    def size(self,name): return len(self.files[name])
    def rename(self,source,target): self.files[target]=self.files.pop(source)
    def delete(self,name): self.files.pop(name,None)
    def close(self): pass


def test_ftp_success_collision_and_overwrite(setup_package,monkeypatch):
    service,payload,root,_=setup_package
    item=build(service,payload)
    ftp=FakeFTP()
    monkeypatch.setattr("app.application.services.weight_package_service.ftplib.FTP",lambda:ftp)
    service.settings.ftp.enabled=True; service.settings.ftp.host="localhost";service.settings.ftp.username="test"
    monkeypatch.setenv(service.settings.ftp.password_env,"test-password")
    uploaded=service.upload(item["id"])
    assert uploaded["ftp_uploaded"] and uploaded["ftp_path"]=="/weights/classify_two_wheel/"+item["package_name"]
    assert ftp.files[item["package_name"]]==Path(item["local_path"]).read_bytes()
    with pytest.raises(ExpConflictError,match="FTP已存在"):
        service.upload(item["id"])
    assert service.upload(item["id"],overwrite=True)["upload_status"]=="succeeded"
    assert list(ftp.files)==[item["package_name"]]


def test_ftp_failure_does_not_mark_uploaded(setup_package,monkeypatch):
    service,payload,root,_=setup_package
    item=build(service,payload);ftp=FakeFTP()
    ftp.storbinary=Mock(side_effect=OSError("secret password must not be persisted"))
    monkeypatch.setattr("app.application.services.weight_package_service.ftplib.FTP",lambda:ftp)
    service.settings.ftp.enabled=True;service.settings.ftp.host="localhost";service.settings.ftp.username="test"
    monkeypatch.setenv(service.settings.ftp.password_env,"test-password")
    with pytest.raises(ExpValidationError,match="FTP上传失败"):service.upload(item["id"])
    result=service.list()["items"][0]
    assert not result["ftp_uploaded"] and result["upload_status"]=="failed"
    assert "secret" not in result["upload_error"]


def test_package_api_preview_build_conflict_and_download(setup_package):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routers.weight_packages import router,get_service
    from app.api.routers import get_request_context
    from app.api.errors.http import install_http_error_handlers
    service,payload,root,_=setup_package
    # TestClient executes endpoints in another thread; share a dedicated SQLite file.
    engine=create_engine("sqlite:///"+str(root/"api-test.db"),connect_args={"check_same_thread":False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for table in (ProjectModel,ExpModel):
            for original in service.session.scalars(select(table)):
                session.add(table(**{c.name:getattr(original,c.name) for c in table.__table__.columns}))
        session.commit()
    def dependency():
        with Session(engine) as session:
            yield WeightPackageService(session,service.settings,root/"api-packages")
    app=FastAPI();app.include_router(router);install_http_error_handlers(app)
    app.dependency_overrides[get_service]=dependency
    app.dependency_overrides[get_request_context]=lambda:SimpleNamespace(request_id="test")
    with TestClient(app) as client:
        preview=client.post('/weight-packages/preview',json=payload)
        assert preview.status_code==200
        body={**payload,"preview_token":preview.json()["data"]["preview_token"]}
        response=client.post('/weight-packages',json=body)
        assert response.status_code==200
        assert client.post('/weight-packages',json=body).status_code==409
        assert client.get('/weight-packages').json()["data"]["total"]==1
        assert client.get('/weight-packages/%s/download'%response.json()["data"]["id"]).status_code==200


def test_onnx_truncated_message_is_rejected(setup_package):
    service,payload,root,_=setup_package
    (root/"bad.onnx").write_bytes(b"\x3a\xff\xff")
    with pytest.raises(ExpValidationError,match="无法读取"):
        service.preview(**{**payload,"platform":"x86","source_file":"bad.onnx","runtime":None})


def test_same_package_is_locked_across_operations(setup_package):
    service,payload,root,_=setup_package
    name=service.preview(**payload)["package_name"]
    with service._lock(name):
        with pytest.raises(ExpConflictError,match="正在打包或上传"):
            build(service,payload)


def test_ftp_failed_replacement_restores_existing_remote_file(setup_package,monkeypatch):
    service,payload,root,_=setup_package
    item=build(service,payload);ftp=FakeFTP()
    service.settings.ftp.enabled=True;service.settings.ftp.host="localhost";service.settings.ftp.username="test"
    monkeypatch.setenv(service.settings.ftp.password_env,"test-password")
    monkeypatch.setattr("app.application.services.weight_package_service.ftplib.FTP",lambda:ftp)
    service.upload(item["id"])
    original=ftp.files[item["package_name"]]
    rename=ftp.rename
    def fail_final_rename(source,target):
        if source.endswith(".part"):
            raise OSError("remote rename denied")
        return rename(source,target)
    ftp.rename=fail_final_rename
    with pytest.raises(ExpValidationError,match="FTP上传失败"):
        service.upload(item["id"],overwrite=True)
    assert ftp.files=={item["package_name"]:original}


@pytest.mark.parametrize("custom_name", ["twowheel_config_v2", "weight_twowheel_config_v2"])
def test_custom_name_new_copy_and_training_metadata(setup_package, custom_name):
    service,payload,root,project=setup_package
    original=build(service,payload)
    custom=build(service,{**payload,"package_name":custom_name})
    assert custom["package_name"]==custom_name+".tgz"
    assert Path(custom["unpacked_path"]).name==custom_name
    script=(Path(custom["unpacked_path"])/"mklink.sh").read_text(encoding="utf-8")
    assert custom_name + "/" + custom_name.removeprefix("weight_") + ".om" in script
    assert (Path(custom["unpacked_path"]) / (custom_name.removeprefix("weight_") + ".om")).read_bytes() == b"valid-model-content"
    assert (Path(custom["unpacked_path"]) / "classify_two_wheel.cfg").is_file()
    assert (Path(custom["unpacked_path"]) / "classify_two_wheel.names").is_file()
    assert custom["model_type"]=="classification"
    assert custom["training_finished_at"].startswith("2026-10-30T18:02:03")
    assert service.list(model_type="classification",project_id=project.id)["total"]==2
    assert service.list(model_type="detection")["total"]==0
    assert service.list(project_id=999)["total"]==0
    assert service.list(upload_status="pending")["total"]==2
    assert Path(original["local_path"]).is_file()
    for name in ("../escape", "/absolute.tgz", "bad name.tgz"):
        with pytest.raises(ExpValidationError):service.preview(**payload,package_name=name)


def test_repack_reads_current_config_and_model(setup_package):
    service,payload,root,project=setup_package
    first=build(service,payload)
    config=json.loads(project.packaging_json)
    config["cfg_content"]+="confidence_threshold=0.2\n"
    project.packaging_json=json.dumps(config)
    service.session.commit()
    (root/"best.om").write_bytes(b"model version 2")
    second=build(service,payload,overwrite=True)
    assert second["id"]==first["id"] and second["sha256"]!=first["sha256"]
    assert (Path(second["unpacked_path"])/(second["package_name"].removeprefix("weight_")[:-4] + ".om")).read_bytes()==b"model version 2"
    assert "confidence_threshold=0.2" in (Path(second["unpacked_path"])/"classify_two_wheel.cfg").read_text()
    assert not second["ftp_uploaded"]
