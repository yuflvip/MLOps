import csv
from datetime import datetime, timezone
import hashlib
from functools import lru_cache
import json
import math
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from app.domain.common.exceptions import (
    ExpConflictError,
    ExpNotFoundError,
    ExpValidationError,
    ProjectNotFoundError,
)
from app.infrastructure.db.models import ExpModel
from app.infrastructure.repositories import ExpRepository, ProjectRepository


PENDING_REVIEW = "pending_review"
APPROVED = "approved"
REJECTED = "rejected"
REVIEW_STATUSES = {PENDING_REVIEW, APPROVED, REJECTED}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
TEXT_EXTENSIONS = {
    ".txt", ".log", ".yaml", ".yml", ".xml", ".md", ".ini", ".cfg",
    ".conf", ".py", ".sh", ".toml", ".html", ".uuid",
}
MODEL_EXTENSIONS = {".pt", ".pth", ".onnx", ".om", ".nb", ".rknn"}
MODEL_ARTIFACT_EXTENSIONS = {".pt", ".pth", ".onnx", ".om", ".bin", ".rknn"}
MAX_TEXT_PREVIEW_BYTES = 1024 * 1024


@lru_cache(maxsize=512)
def _md5_cached(path: str, size_bytes: int, modified_ns: int) -> str:
    del size_bytes, modified_ns
    digest = hashlib.md5()
    with Path(path).open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _serialize_exp(exp: ExpModel) -> Dict[str, Any]:
    return {
        "id": exp.id,
        "project_id": exp.project_id,
        "name": exp.name,
        "relative_path": exp.relative_path,
        "resolved_path": exp.resolved_path,
        "review_status": exp.review_status,
        "version": exp.version,
        "description": exp.description,
        "review_comment": exp.review_comment,
        "imported_at": exp.imported_at.isoformat(),
        "reviewed_at": exp.reviewed_at.isoformat() if exp.reviewed_at else None,
        "created_at": exp.created_at.isoformat(),
        "updated_at": exp.updated_at.isoformat(),
    }


class ExpService:
    def __init__(self, *, exp_repository: ExpRepository, project_repository: ProjectRepository) -> None:
        self._exp_repository = exp_repository
        self._project_repository = project_repository

    def list_exps(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        project_id: Optional[int] = None,
        review_status: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        if review_status and review_status not in REVIEW_STATUSES:
            raise ExpValidationError("Exp review_status is invalid")
        if model_type and model_type not in {"classification", "detection", "segmentation"}:
            raise ExpValidationError("Exp model_type is invalid")
        items, total = self._exp_repository.list_paginated(
            page=page,
            page_size=page_size,
            project_id=project_id,
            review_status=review_status,
            model_type=model_type,
        )
        return {
            "items": [self._serialize_exp_with_metric(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_exp(self, exp_id: int) -> Dict[str, Any]:
        exp = self._get_exp(exp_id)
        self._get_existing_exp_root(exp)
        return self._serialize_exp_with_metric(exp)

    def _serialize_exp_with_metric(self, exp: ExpModel) -> Dict[str, Any]:
        result = _serialize_exp(exp)
        root = Path(exp.resolved_path).resolve()
        if not root.is_dir():
            result["validation_metric_value"] = None
            result["training_started_at"] = None
            result["training_finished_at"] = None
            return result

        args_path = next(
            (path for path in (root / "args.json", root / "args.yaml") if path.is_file()),
            None,
        )
        results_path = root / "results.png"
        result["validation_metric_value"] = self._validation_metric(root / "results.csv")
        result["training_started_at"] = (
            self._file_timestamp(args_path).isoformat() if args_path else None
        )
        result["training_finished_at"] = (
            self._file_timestamp(results_path).isoformat()
            if results_path.is_file()
            else None
        )
        return result

    def list_artifacts(self, exp_id: int) -> Dict[str, Any]:
        exp = self._get_exp(exp_id)
        root = self._get_existing_exp_root(exp)
        items = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if not resolved.is_relative_to(root):
                continue
            stat = resolved.stat()
            extension = resolved.suffix.lower()
            media_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
            items.append(
                {
                    "name": resolved.name,
                    "relative_path": resolved.relative_to(root).as_posix(),
                    "extension": extension.removeprefix("."),
                    "media_type": media_type,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    "preview_kind": self._preview_kind(extension),
                }
            )
        items.sort(key=lambda item: item["relative_path"].lower())
        return {"items": items, "total": len(items)}

    def list_model_artifacts(self, exp_id: int) -> Dict[str, Any]:
        exp = self._get_exp(exp_id)
        root = self._get_existing_exp_root(exp)
        items = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in MODEL_ARTIFACT_EXTENSIONS:
                continue
            resolved = path.resolve()
            if not resolved.is_relative_to(root):
                continue
            stat = resolved.stat()
            extension = resolved.suffix.lower()
            items.append(
                {
                    "name": resolved.name,
                    "relative_path": resolved.relative_to(root).as_posix(),
                    "extension": extension.removeprefix("."),
                    "media_type": (
                        mimetypes.guess_type(resolved.name)[0]
                        or "application/octet-stream"
                    ),
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    "preview_kind": self._preview_kind(extension),
                    "md5": self._md5(resolved),
                }
            )
        items.sort(key=lambda item: item["relative_path"].lower())
        return {"items": items, "total": len(items)}

    def preview_artifact(
        self,
        exp_id: int,
        *,
        relative_path: str,
        page: int = 1,
        page_size: int = 100,
        sheet_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        path, normalized_relative_path = self.resolve_artifact(exp_id, relative_path)
        kind = self._preview_kind(path.suffix.lower())
        base = {
            "relative_path": normalized_relative_path,
            "preview_kind": kind,
            "page": page,
            "page_size": page_size,
        }
        if kind in {"image", "pdf", "binary", "unsupported"}:
            return base
        if kind in {"text", "json"}:
            size = path.stat().st_size
            with path.open("rb") as file_handle:
                raw = file_handle.read(MAX_TEXT_PREVIEW_BYTES + 1)
            truncated = len(raw) > MAX_TEXT_PREVIEW_BYTES
            content = raw[:MAX_TEXT_PREVIEW_BYTES].decode("utf-8", errors="replace")
            if kind == "json":
                try:
                    content = json.dumps(json.loads(content), ensure_ascii=False, indent=2)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            return {**base, "content": content, "truncated": truncated or size > len(raw)}
        if kind == "table":
            return {**base, **self._preview_delimited(path, page, page_size)}
        if kind == "xlsx":
            return {**base, **self._preview_xlsx(path, page, page_size, sheet_name)}
        return base

    def resolve_artifact(self, exp_id: int, relative_path: str):
        exp = self._get_exp(exp_id)
        root = self._get_existing_exp_root(exp)
        raw_path = Path(relative_path)
        if not relative_path.strip() or raw_path.is_absolute():
            raise ExpValidationError("Artifact path must be a non-empty relative path")
        resolved = (root / raw_path).resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ExpValidationError("Artifact file was not found under the exp directory")
        return resolved, resolved.relative_to(root).as_posix()

    def scan_candidates(self, project_id: int) -> Dict[str, Any]:
        project, root = self._get_project_root(project_id)
        if not root.exists() or not root.is_dir():
            raise ExpValidationError("Project exp_root_path does not exist or is not a directory")
        items = []
        for child in sorted(root.iterdir(), key=lambda path: path.name.lower()):
            if not child.is_dir():
                continue
            resolved = child.resolve()
            if not resolved.is_relative_to(root):
                continue
            relative_path = child.name
            modified_at = datetime.fromtimestamp(child.stat().st_mtime, tz=timezone.utc)
            items.append(
                {
                    "name": child.name,
                    "relative_path": relative_path,
                    "modified_at": modified_at.isoformat(),
                    "already_imported": self._exp_repository.get_by_project_path(
                        project.id, relative_path
                    ) is not None,
                }
            )
        return {"project_id": project.id, "exp_root_path": str(root), "items": items}

    def import_exps(self, project_id: int, relative_paths: List[str]) -> List[Dict[str, Any]]:
        project, root = self._get_project_root(project_id)
        if not isinstance(relative_paths, list) or not relative_paths:
            raise ExpValidationError("Exp relative_paths must be a non-empty list")
        normalized_paths = []
        for raw_path in relative_paths:
            relative_path = raw_path.strip() if isinstance(raw_path, str) else ""
            if not relative_path or Path(relative_path).is_absolute() or len(Path(relative_path).parts) != 1:
                raise ExpValidationError("Exp relative_path must be a first-level directory name")
            if relative_path in normalized_paths:
                raise ExpValidationError("Exp relative_paths must not contain duplicates")
            candidate = (root / relative_path).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_dir():
                raise ExpValidationError("Exp directory was not found under project exp_root_path")
            if self._exp_repository.get_by_project_path(project.id, relative_path):
                raise ExpConflictError("Exp directory '%s' has already been imported" % relative_path)
            normalized_paths.append(relative_path)

        try:
            saved = [
                self._exp_repository.add(
                    ExpModel(
                        project_id=project.id,
                        name=relative_path,
                        relative_path=relative_path,
                        resolved_path=str((root / relative_path).resolve()),
                        review_status=PENDING_REVIEW,
                    )
                )
                for relative_path in normalized_paths
            ]
            self._exp_repository.commit()
        except Exception:
            self._exp_repository.rollback()
            raise
        return [_serialize_exp(item) for item in saved]

    def approve_exp(self, exp_id: int, *, version: str, description: Optional[str]) -> Dict[str, Any]:
        exp = self._exp_repository.get_by_id(exp_id)
        if exp is None:
            raise ExpNotFoundError("Exp '%s' was not found" % exp_id)
        if exp.review_status == APPROVED:
            raise ExpConflictError("Exp '%s' has already been approved" % exp_id)
        normalized_version = version.strip()
        if not normalized_version:
            raise ExpValidationError("Exp version must not be empty")
        existing = self._exp_repository.get_by_project_version(exp.project_id, normalized_version)
        if existing is not None:
            raise ExpConflictError("Exp version '%s' already exists in this project" % normalized_version)
        exp.version = normalized_version
        exp.description = description.strip() if isinstance(description, str) and description.strip() else None
        exp.review_comment = None
        exp.review_status = APPROVED
        exp.reviewed_at = datetime.now(timezone.utc)
        saved = self._exp_repository.add(exp)
        self._exp_repository.commit()
        return _serialize_exp(saved)

    def reject_exp(self, exp_id: int, *, review_comment: str) -> Dict[str, Any]:
        exp = self._get_exp(exp_id)
        if exp.review_status == APPROVED:
            raise ExpConflictError("Approved exp '%s' cannot be rejected" % exp_id)
        normalized_comment = review_comment.strip()
        if not normalized_comment:
            raise ExpValidationError("Exp review_comment must not be empty")
        exp.review_status = REJECTED
        exp.review_comment = normalized_comment
        exp.version = None
        exp.reviewed_at = datetime.now(timezone.utc)
        saved = self._exp_repository.add(exp)
        self._exp_repository.commit()
        return _serialize_exp(saved)

    def delete_exp(self, exp_id: int) -> bool:
        exp = self._get_exp(exp_id)
        if exp.review_status == APPROVED:
            raise ExpConflictError("Approved exp '%s' cannot be deleted" % exp_id)
        self._exp_repository.delete(exp)
        self._exp_repository.commit()
        return True

    def _get_project_root(self, project_id: int):
        project = self._project_repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError("Project '%s' was not found" % project_id)
        if not project.exp_root_path:
            raise ExpValidationError("Project exp_root_path is not configured")
        return project, Path(project.exp_root_path).resolve()

    def _get_exp(self, exp_id: int) -> ExpModel:
        exp = self._exp_repository.get_by_id(exp_id)
        if exp is None:
            raise ExpNotFoundError("Exp '%s' was not found" % exp_id)
        return exp

    def _get_existing_exp_root(self, exp: ExpModel) -> Path:
        root = Path(exp.resolved_path).resolve()
        if not root.exists() or not root.is_dir():
            raise ExpValidationError("Exp directory does not exist or is not a directory")
        return root

    def _file_timestamp(self, path: Path) -> datetime:
        stat = path.stat()
        timestamp = getattr(stat, "st_birthtime", stat.st_mtime)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def _md5(self, path: Path) -> str:
        stat = path.stat()
        return _md5_cached(str(path), stat.st_size, stat.st_mtime_ns)

    def _validation_metric(self, results_path: Path) -> Optional[float]:
        if not results_path.is_file():
            return None
        try:
            with results_path.open(
                "r",
                encoding="utf-8-sig",
                errors="replace",
                newline="",
            ) as handle:
                reader = csv.reader(handle)
                headers = [header.strip() for header in next(reader, [])]
                target_index = next(
                    (
                        index
                        for index, header in enumerate(headers)
                        if header == "val_acc_top1"
                    ),
                    None,
                )
                if target_index is None:
                    target_index = next(
                        (
                            index
                            for index, header in enumerate(headers)
                            if "map50-95" in header.lower()
                        ),
                        None,
                    )
                if target_index is None:
                    return None

                values = []
                for row in reader:
                    if target_index >= len(row):
                        continue
                    try:
                        value = float(row[target_index].strip())
                    except ValueError:
                        continue
                    if math.isfinite(value):
                        values.append(value)
                return max(values) if values else None
        except OSError:
            return None

    def _preview_kind(self, extension: str) -> str:
        if extension in IMAGE_EXTENSIONS:
            return "image"
        if extension == ".pdf":
            return "pdf"
        if extension == ".json":
            return "json"
        if extension in {".csv", ".tsv"}:
            return "table"
        if extension == ".xlsx":
            return "xlsx"
        if extension == ".xls":
            return "unsupported"
        if extension in TEXT_EXTENSIONS:
            return "text"
        if extension in MODEL_EXTENSIONS:
            return "binary"
        return "unsupported"

    def _preview_delimited(self, path: Path, page: int, page_size: int) -> Dict[str, Any]:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        start = (page - 1) * page_size
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            columns = next(reader, [])
            rows = []
            for index, row in enumerate(reader):
                if index < start:
                    continue
                if len(rows) >= page_size + 1:
                    break
                rows.append(row)
        return {
            "columns": columns,
            "rows": rows[:page_size],
            "has_more": len(rows) > page_size,
        }

    def _preview_xlsx(
        self,
        path: Path,
        page: int,
        page_size: int,
        selected_sheet: Optional[str],
    ) -> Dict[str, Any]:
        try:
            with ZipFile(path) as workbook:
                shared_strings = self._xlsx_shared_strings(workbook)
                sheets = self._xlsx_sheets(workbook)
                sheet_names = list(sheets)
                sheet_name = selected_sheet if selected_sheet in sheets else (sheet_names[0] if sheet_names else None)
                if sheet_name is None:
                    return {"sheet_names": [], "rows": [], "columns": []}
                rows = self._xlsx_rows(
                    workbook,
                    sheets[sheet_name],
                    shared_strings,
                    start=(page - 1) * page_size,
                    limit=page_size + 1,
                )
        except (BadZipFile, KeyError, ElementTree.ParseError) as exc:
            raise ExpValidationError("XLSX file could not be parsed") from exc
        width = max((len(row) for row in rows[:page_size]), default=0)
        return {
            "sheet_names": sheet_names,
            "sheet_name": sheet_name,
            "columns": [self._excel_column_name(index + 1) for index in range(width)],
            "rows": rows[:page_size],
            "has_more": len(rows) > page_size,
        }

    def _xlsx_shared_strings(self, workbook: ZipFile) -> List[str]:
        if "xl/sharedStrings.xml" not in workbook.namelist():
            return []
        root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
        return ["".join(node.itertext()) for node in root]

    def _xlsx_sheets(self, workbook: ZipFile) -> Dict[str, str]:
        ns = {
            "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
            "p": "http://schemas.openxmlformats.org/package/2006/relationships",
        }
        workbook_root = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
        rels_root = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        relationships = {
            node.attrib["Id"]: node.attrib["Target"] for node in rels_root.findall("p:Relationship", ns)
        }
        result = {}
        for sheet in workbook_root.findall("m:sheets/m:sheet", ns):
            target = relationships[sheet.attrib["{%s}id" % ns["r"]]].lstrip("/")
            result[sheet.attrib["name"]] = target if target.startswith("xl/") else "xl/" + target
        return result

    def _xlsx_rows(
        self, workbook: ZipFile, sheet_path: str, shared_strings: List[str], *, start: int, limit: int
    ) -> List[List[Any]]:
        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        root = ElementTree.fromstring(workbook.read(sheet_path))
        result = []
        for row_index, row_node in enumerate(root.iter(ns + "row")):
            if row_index < start:
                continue
            values = []
            for cell in row_node.findall(ns + "c"):
                cell_type = cell.attrib.get("t")
                value_node = cell.find(ns + "v")
                value: Any = value_node.text if value_node is not None else ""
                if cell_type == "s" and value != "":
                    value = shared_strings[int(value)]
                elif cell_type == "inlineStr":
                    inline = cell.find(ns + "is")
                    value = "".join(inline.itertext()) if inline is not None else ""
                values.append(value)
            result.append(values)
            if len(result) >= limit:
                break
        return result

    def _excel_column_name(self, index: int) -> str:
        name = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            name = chr(65 + remainder) + name
        return name
