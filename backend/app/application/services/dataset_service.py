import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.domain.common.exceptions import (
    DatasetConflictError,
    DatasetNotFoundError,
    DatasetValidationError,
)
from app.infrastructure.db.models import DatasetModel
from app.infrastructure.repositories import DatasetRepository


def _serialize_dataset(dataset: DatasetModel) -> Dict[str, Any]:
    return {
        "id": dataset.id,
        "name": dataset.name,
        "path": dataset.path,
        "task_type": dataset.task_type,
        "class_names": json.loads(dataset.class_names_json),
        "description": dataset.description,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None,
    }


class DatasetService:
    def __init__(self, dataset_repository: DatasetRepository) -> None:
        self._dataset_repository = dataset_repository

    def list_datasets(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        name: Optional[str] = None,
        path: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        items, total = self._dataset_repository.list_paginated(
            page=page,
            page_size=page_size,
            name=name.strip() if isinstance(name, str) and name.strip() else None,
            path=path.strip() if isinstance(path, str) and path.strip() else None,
            task_type=(
                task_type.strip()
                if isinstance(task_type, str) and task_type.strip()
                else None
            ),
        )
        return {
            "items": [_serialize_dataset(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_dataset(self, dataset_id: int) -> Dict[str, Any]:
        dataset = self._dataset_repository.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFoundError(
                "Dataset '%s' was not found" % dataset_id
            )
        return _serialize_dataset(dataset)

    def create_dataset(
        self,
        *,
        name: str,
        path: str,
        task_type: Optional[str],
        class_names: List[str],
        description: Optional[str],
    ) -> Dict[str, Any]:
        normalized = self._validate_payload(
            name=name,
            path=path,
            task_type=task_type,
            class_names=class_names,
            description=description,
        )
        self._assert_unique_name(normalized["name"])
        self._assert_unique_path(normalized["path"])

        dataset = self._dataset_repository.add(
            DatasetModel(
                name=normalized["name"],
                path=normalized["path"],
                task_type=normalized["task_type"],
                class_names_json=json.dumps(normalized["class_names"], ensure_ascii=True),
                description=normalized["description"],
            )
        )
        self._dataset_repository.commit()
        return _serialize_dataset(dataset)

    def update_dataset(
        self,
        dataset_id: int,
        *,
        name: str,
        path: str,
        task_type: Optional[str],
        class_names: List[str],
        description: Optional[str],
    ) -> Dict[str, Any]:
        dataset = self._dataset_repository.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFoundError(
                "Dataset '%s' was not found" % dataset_id
            )

        normalized = self._validate_payload(
            name=name,
            path=path,
            task_type=task_type,
            class_names=class_names,
            description=description,
        )
        self._assert_unique_name(normalized["name"], exclude_id=dataset_id)
        self._assert_unique_path(normalized["path"], exclude_id=dataset_id)

        dataset.name = normalized["name"]
        dataset.path = normalized["path"]
        dataset.task_type = normalized["task_type"]
        dataset.class_names_json = json.dumps(
            normalized["class_names"],
            ensure_ascii=True,
        )
        dataset.description = normalized["description"]
        saved = self._dataset_repository.save(dataset)
        self._dataset_repository.commit()
        return _serialize_dataset(saved)

    def delete_dataset(self, dataset_id: int) -> bool:
        dataset = self._dataset_repository.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFoundError(
                "Dataset '%s' was not found" % dataset_id
            )
        self._dataset_repository.delete(dataset)
        self._dataset_repository.commit()
        return True

    def _assert_unique_name(self, name: str, exclude_id: Optional[int] = None) -> None:
        existing = self._dataset_repository.get_by_name(name)
        if existing is not None and existing.id != exclude_id:
            raise DatasetConflictError("Dataset name '%s' already exists" % name)

    def _assert_unique_path(self, path: str, exclude_id: Optional[int] = None) -> None:
        existing = self._dataset_repository.get_by_path(path)
        if existing is not None and existing.id != exclude_id:
            raise DatasetConflictError("Dataset path '%s' already exists" % path)

    def _validate_payload(
        self,
        *,
        name: str,
        path: str,
        task_type: Optional[str],
        class_names: List[str],
        description: Optional[str],
    ) -> Dict[str, Any]:
        normalized_name = name.strip()
        if not normalized_name:
            raise DatasetValidationError("Dataset name must not be empty")

        normalized_path = path.strip()
        if not normalized_path:
            raise DatasetValidationError("Dataset path must not be empty")
        if not Path(normalized_path).is_absolute():
            raise DatasetValidationError("Dataset path must be an absolute path")

        if not isinstance(class_names, list) or not class_names:
            raise DatasetValidationError("Dataset class_names must be a non-empty list")

        normalized_class_names: List[str] = []
        seen = set()
        for raw_name in class_names:
            if not isinstance(raw_name, str):
                raise DatasetValidationError("Dataset class_names must contain only strings")
            normalized_class_name = raw_name.strip()
            if not normalized_class_name:
                raise DatasetValidationError("Dataset class_names must not contain empty values")
            if normalized_class_name in seen:
                raise DatasetValidationError("Dataset class_names must not contain duplicates")
            normalized_class_names.append(normalized_class_name)
            seen.add(normalized_class_name)

        normalized_task_type = task_type.strip() if isinstance(task_type, str) else None
        if normalized_task_type == "":
            normalized_task_type = None
        normalized_description = description.strip() if isinstance(description, str) else None
        if normalized_description == "":
            normalized_description = None

        return {
            "name": normalized_name,
            "path": normalized_path,
            "task_type": normalized_task_type,
            "class_names": normalized_class_names,
            "description": normalized_description,
        }
