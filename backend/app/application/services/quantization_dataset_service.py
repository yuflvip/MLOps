import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.domain.common.exceptions import (
    QuantizationDatasetConflictError,
    QuantizationDatasetNotFoundError,
    QuantizationDatasetValidationError,
)
from app.infrastructure.db.models import QuantizationDatasetModel
from app.infrastructure.repositories import QuantizationDatasetRepository


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
IMAGE_LIST_FILENAME = "ref_img_list.txt"


def _utc_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _serialize_dataset(dataset: QuantizationDatasetModel) -> Dict[str, Any]:
    storage_path = Path(dataset.storage_path)
    return {
        "id": dataset.id,
        "name": dataset.name,
        "storage_path": dataset.storage_path,
        "image_list_path": str(storage_path / IMAGE_LIST_FILENAME),
        "image_count": dataset.image_count,
        "size_bytes": dataset.size_bytes,
        "description": dataset.description,
        "created_at": _utc_iso(dataset.created_at),
        "updated_at": _utc_iso(dataset.updated_at),
    }


class QuantizationDatasetService:
    def __init__(
        self,
        repository: QuantizationDatasetRepository,
        *,
        storage_root: Path,
        max_image_size_mb: int,
    ) -> None:
        self._repository = repository
        self._storage_root = storage_root.resolve()
        self._max_image_size_bytes = max_image_size_mb * 1024 * 1024

    def list_datasets(
        self, *, page: int, page_size: int, name: Optional[str]
    ) -> Dict[str, Any]:
        items, total = self._repository.list_paginated(
            page=page, page_size=page_size, name=name
        )
        return {
            "items": [_serialize_dataset(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_dataset(self, dataset_id: int) -> Dict[str, Any]:
        return _serialize_dataset(self._get_dataset(dataset_id))

    def create_dataset(
        self, *, name: str, description: Optional[str]
    ) -> Dict[str, Any]:
        normalized_name = self._normalize_name(name)
        if self._repository.get_by_name(normalized_name):
            raise QuantizationDatasetConflictError(
                f"量化数据集名称“{normalized_name}”已存在"
            )
        self._storage_root.mkdir(parents=True, exist_ok=True)
        storage_path = self._storage_root / uuid.uuid4().hex
        images_path = storage_path / "images"
        try:
            images_path.mkdir(parents=True)
            self._write_image_list(storage_path)
            dataset = self._repository.add(
                QuantizationDatasetModel(
                    name=normalized_name,
                    storage_path=str(storage_path),
                    image_count=0,
                    size_bytes=0,
                    description=self._normalize_description(description),
                )
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            shutil.rmtree(storage_path, ignore_errors=True)
            raise
        return _serialize_dataset(dataset)

    def update_dataset(
        self, dataset_id: int, *, name: str, description: Optional[str]
    ) -> Dict[str, Any]:
        dataset = self._get_dataset(dataset_id)
        normalized_name = self._normalize_name(name)
        existing = self._repository.get_by_name(normalized_name)
        if existing and existing.id != dataset_id:
            raise QuantizationDatasetConflictError(
                f"量化数据集名称“{normalized_name}”已存在"
            )
        dataset.name = normalized_name
        dataset.description = self._normalize_description(description)
        self._repository.commit()
        return _serialize_dataset(dataset)

    def delete_dataset(self, dataset_id: int) -> bool:
        dataset = self._get_dataset(dataset_id)
        storage_path = self._validated_storage_path(dataset)
        self._repository.delete(dataset)
        self._repository.commit()
        if storage_path.exists():
            shutil.rmtree(storage_path)
        return True

    def list_images(
        self, dataset_id: int, *, page: int, page_size: int
    ) -> Dict[str, Any]:
        dataset = self._get_dataset(dataset_id)
        images = self._scan_images(dataset)
        start = (page - 1) * page_size
        return {
            "items": images[start : start + page_size],
            "total": len(images),
            "page": page,
            "page_size": page_size,
        }

    def upload_image(
        self, dataset_id: int, *, filename: str, content: bytes
    ) -> Dict[str, Any]:
        dataset = self._get_dataset(dataset_id)
        safe_name = self._validate_filename(filename)
        if not content:
            raise QuantizationDatasetValidationError("图片文件不能为空")
        if len(content) > self._max_image_size_bytes:
            raise QuantizationDatasetValidationError(
                f"单张图片不能超过 {self._max_image_size_bytes // 1024 // 1024} MB"
            )
        images_path = self._validated_storage_path(dataset) / "images"
        target = images_path / safe_name
        temp_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=images_path, prefix=".upload-", delete=False
            ) as temp_file:
                temp_file.write(content)
                temp_path = Path(temp_file.name)
            os.replace(temp_path, target)
            self._sync_dataset_files(dataset)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            if temp_path and temp_path.exists():
                temp_path.unlink()
            if target.exists():
                target.unlink()
            raise
        image = self._serialize_image(target)
        return {"image": image, "dataset": _serialize_dataset(dataset)}

    def delete_images(self, dataset_id: int, names: List[str]) -> Dict[str, Any]:
        dataset = self._get_dataset(dataset_id)
        images_path = self._validated_storage_path(dataset) / "images"
        normalized_names = list(dict.fromkeys(self._validate_filename(n) for n in names))
        targets = [images_path / name for name in normalized_names]
        missing = [path.name for path in targets if not path.is_file()]
        if missing:
            raise QuantizationDatasetValidationError(
                f"图片不存在：{', '.join(missing)}"
            )
        for target in targets:
            target.unlink()
        self._sync_dataset_files(dataset)
        self._repository.commit()
        return _serialize_dataset(dataset)

    def resolve_image(self, dataset_id: int, filename: str) -> Path:
        dataset = self._get_dataset(dataset_id)
        safe_name = self._validate_filename(filename)
        target = self._validated_storage_path(dataset) / "images" / safe_name
        if not target.is_file():
            raise QuantizationDatasetNotFoundError(f"图片“{safe_name}”不存在")
        return target

    def resolve_image_list(self, dataset_id: int) -> Path:
        dataset = self._get_dataset(dataset_id)
        target = self._validated_storage_path(dataset) / IMAGE_LIST_FILENAME
        if not target.is_file():
            self._write_image_list(target.parent)
        return target

    def _get_dataset(self, dataset_id: int) -> QuantizationDatasetModel:
        dataset = self._repository.get_by_id(dataset_id)
        if dataset is None:
            raise QuantizationDatasetNotFoundError(
                f"量化数据集 ID {dataset_id} 不存在"
            )
        return dataset

    def _validated_storage_path(self, dataset: QuantizationDatasetModel) -> Path:
        path = Path(dataset.storage_path).resolve()
        if path.parent != self._storage_root:
            raise QuantizationDatasetValidationError("量化数据集存储路径不安全")
        return path

    def _scan_images(self, dataset: QuantizationDatasetModel) -> List[Dict[str, Any]]:
        images_path = self._validated_storage_path(dataset) / "images"
        if not images_path.exists():
            return []
        return [
            self._serialize_image(path)
            for path in sorted(images_path.iterdir(), key=lambda item: item.name.lower())
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
        ]

    @staticmethod
    def _serialize_image(path: Path) -> Dict[str, Any]:
        stat = path.stat()
        return {
            "name": path.name,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
        }

    def _sync_dataset_files(self, dataset: QuantizationDatasetModel) -> None:
        storage_path = self._validated_storage_path(dataset)
        images = self._scan_images(dataset)
        dataset.image_count = len(images)
        dataset.size_bytes = sum(item["size_bytes"] for item in images)
        dataset.updated_at = datetime.now(timezone.utc)
        self._write_image_list(storage_path)

    @staticmethod
    def _write_image_list(storage_path: Path) -> None:
        images_path = storage_path / "images"
        image_paths = [
            str(path.resolve())
            for path in sorted(images_path.iterdir(), key=lambda item: item.name.lower())
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
        ]
        target = storage_path / IMAGE_LIST_FILENAME
        temp = storage_path / f".{IMAGE_LIST_FILENAME}.tmp"
        text = "".join(f"{path}\n" for path in image_paths)
        temp.write_text(text, encoding="utf-8")
        os.replace(temp, target)

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise QuantizationDatasetValidationError("量化数据集名称不能为空")
        if len(normalized) > 128:
            raise QuantizationDatasetValidationError("量化数据集名称不能超过128个字符")
        return normalized

    @staticmethod
    def _normalize_description(description: Optional[str]) -> Optional[str]:
        normalized = (description or "").strip()
        return normalized or None

    @staticmethod
    def _validate_filename(filename: str) -> str:
        normalized = filename.strip()
        if (
            not normalized
            or normalized in {".", ".."}
            or Path(normalized).name != normalized
            or "\x00" in normalized
        ):
            raise QuantizationDatasetValidationError("图片文件名不合法")
        if Path(normalized).suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            allowed = "、".join(sorted(SUPPORTED_IMAGE_SUFFIXES))
            raise QuantizationDatasetValidationError(
                f"仅支持以下图片格式：{allowed}"
            )
        return normalized
