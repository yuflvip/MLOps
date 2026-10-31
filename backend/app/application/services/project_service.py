import json
from pathlib import Path
from pydantic import ValidationError
from app.domain.common.packaging import ProjectPackagingConfig
from typing import Any, Dict, List, Optional

from app.domain.common.exceptions import (
    DatasetNotFoundError,
    ProjectConflictError,
    ProjectNotFoundError,
    ProjectValidationError,
)
from app.infrastructure.db.models import ProjectModel
from app.infrastructure.repositories import DatasetRepository, ProjectRepository

MODEL_TYPES = {"classification", "detection", "segmentation"}
MODEL_ARCHITECTURES_BY_TYPE = {
    "classification": {"HGNetV2", "EC", "unknown"},
    "detection": {"YOLOv26", "YOLOv8", "unknown"},
    "segmentation": {"unknown"},
}


def _project_packaging(packaging, project_key):
    values = dict(packaging or {})
    values.pop("package_key", None)
    values["cfg_filename"] = project_key + ".cfg"
    values["names_filename"] = project_key + ".names"
    return ProjectPackagingConfig.model_validate(values).model_dump()


def _serialize_project(project: ProjectModel) -> Dict[str, Any]:
    return {
        "id": project.id,
        "project": project.project,
        "name": project.name,
        "model_type": project.model_type,
        "model_architecture": project.model_architecture,
        "description": project.description,
        "exp_root_path": project.exp_root_path,
        "packaging": _project_packaging(json.loads(project.packaging_json or "{}"), project.project),
        "dataset_ids": json.loads(project.dataset_ids_json),
        "epochs": project.epochs,
        "batch": project.batch,
        "imgsz": project.imgsz,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


class ProjectService:
    def __init__(
        self,
        *,
        project_repository: ProjectRepository,
        dataset_repository: DatasetRepository,
    ) -> None:
        self._project_repository = project_repository
        self._dataset_repository = dataset_repository

    def list_projects(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        project: Optional[str] = None,
        name: Optional[str] = None,
        model_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Dict[str, Any]:
        items, total = self._project_repository.list_paginated(
            keyword=keyword.strip() if isinstance(keyword, str) and keyword.strip() else None,
            page=page,
            page_size=page_size,
            project=project.strip() if isinstance(project, str) and project.strip() else None,
            name=name.strip() if isinstance(name, str) and name.strip() else None,
            model_type=(
                model_type.strip()
                if isinstance(model_type, str) and model_type.strip()
                else None
            ),
        )
        return {
            "items": [_serialize_project(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_project(self, project_id: int) -> Dict[str, Any]:
        project = self._project_repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError("Project '%s' was not found" % project_id)
        return _serialize_project(project)

    def create_project(
        self,
        *,
        project: str,
        name: str,
        model_type: str,
        model_architecture: str,
        description: Optional[str],
        exp_root_path: str,
        dataset_ids: List[int],
        epochs: Optional[int],
        batch: Optional[int],
        imgsz: Optional[int],
        packaging: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized = self._validate_payload(
            project=project,
            name=name,
            model_type=model_type,
            model_architecture=model_architecture,
            description=description,
            exp_root_path=exp_root_path,
            dataset_ids=dataset_ids,
            epochs=epochs,
            batch=batch,
            imgsz=imgsz,
        )
        packaging_json = self._validate_packaging(packaging, normalized["project"])
        self._assert_unique_project(normalized["project"])
        saved = self._project_repository.add(
            ProjectModel(
                packaging_json=packaging_json,
                project=normalized["project"],
                name=normalized["name"],
                model_type=normalized["model_type"],
                model_architecture=normalized["model_architecture"],
                description=normalized["description"],
                exp_root_path=normalized["exp_root_path"],
                dataset_ids_json=json.dumps(normalized["dataset_ids"], ensure_ascii=True),
                epochs=normalized["epochs"],
                batch=normalized["batch"],
                imgsz=normalized["imgsz"],
            )
        )
        self._project_repository.commit()
        return _serialize_project(saved)

    def update_project(
        self,
        project_id: int,
        *,
        project: str,
        name: str,
        model_type: str,
        model_architecture: str,
        description: Optional[str],
        exp_root_path: str,
        dataset_ids: List[int],
        epochs: Optional[int],
        batch: Optional[int],
        imgsz: Optional[int],
        packaging: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        existing = self._project_repository.get_by_id(project_id)
        if existing is None:
            raise ProjectNotFoundError("Project '%s' was not found" % project_id)

        normalized = self._validate_payload(
            project=project,
            name=name,
            model_type=model_type,
            model_architecture=model_architecture,
            description=description,
            exp_root_path=exp_root_path,
            dataset_ids=dataset_ids,
            epochs=epochs,
            batch=batch,
            imgsz=imgsz,
        )
        self._assert_unique_project(normalized["project"], exclude_id=project_id)
        existing.packaging_json = self._validate_packaging(
            packaging if packaging is not None else json.loads(existing.packaging_json or "{}"),
            normalized["project"],
        )
        existing.project = normalized["project"]
        existing.name = normalized["name"]
        existing.model_type = normalized["model_type"]
        existing.model_architecture = normalized["model_architecture"]
        existing.description = normalized["description"]
        existing.exp_root_path = normalized["exp_root_path"]
        existing.dataset_ids_json = json.dumps(normalized["dataset_ids"], ensure_ascii=True)
        existing.epochs = normalized["epochs"]
        existing.batch = normalized["batch"]
        existing.imgsz = normalized["imgsz"]
        saved = self._project_repository.save(existing)
        self._project_repository.commit()
        return _serialize_project(saved)

    def _validate_packaging(self, packaging: Optional[Dict[str, Any]], project_key: str) -> str:
        try:
            config = ProjectPackagingConfig.model_validate(_project_packaging(packaging, project_key))
        except ValidationError as exc:
            raise ProjectValidationError(str(exc)) from exc
        return config.model_dump_json()

    def delete_project(self, project_id: int) -> bool:
        existing = self._project_repository.get_by_id(project_id)
        if existing is None:
            raise ProjectNotFoundError("Project '%s' was not found" % project_id)
        self._project_repository.delete(existing)
        self._project_repository.commit()
        return True

    def _assert_unique_project(self, project: str, exclude_id: Optional[int] = None) -> None:
        existing = self._project_repository.get_by_project(project)
        if existing is not None and existing.id != exclude_id:
            raise ProjectConflictError("Project key '%s' already exists" % project)

    def _validate_payload(
        self,
        *,
        project: str,
        name: str,
        model_type: str,
        model_architecture: str,
        description: Optional[str],
        exp_root_path: str,
        dataset_ids: List[int],
        epochs: Optional[int],
        batch: Optional[int],
        imgsz: Optional[int],
    ) -> Dict[str, Any]:
        normalized_project = project.strip()
        if not normalized_project:
            raise ProjectValidationError("Project key must not be empty")

        normalized_name = name.strip()
        if not normalized_name:
            raise ProjectValidationError("Project name must not be empty")

        normalized_model_type = model_type.strip()
        if normalized_model_type not in MODEL_TYPES:
            raise ProjectValidationError(
                "Project model_type must be one of classification, detection, segmentation"
            )

        normalized_model_architecture = model_architecture.strip()
        if normalized_model_architecture not in MODEL_ARCHITECTURES_BY_TYPE[
            normalized_model_type
        ]:
            raise ProjectValidationError(
                "Project model_architecture is not valid for project model_type"
            )

        normalized_exp_root_path = exp_root_path.strip()
        if not normalized_exp_root_path:
            raise ProjectValidationError("Project exp_root_path must not be empty")
        if not Path(normalized_exp_root_path).is_absolute():
            raise ProjectValidationError("Project exp_root_path must be an absolute path")

        if not isinstance(dataset_ids, list) or not dataset_ids:
            raise ProjectValidationError("Project dataset_ids must be a non-empty list")

        normalized_dataset_ids: List[int] = []
        seen = set()
        for raw_id in dataset_ids:
            if not isinstance(raw_id, int):
                raise ProjectValidationError("Project dataset_ids must contain only integers")
            if raw_id <= 0:
                raise ProjectValidationError("Project dataset_ids must contain only positive integers")
            if raw_id in seen:
                raise ProjectValidationError("Project dataset_ids must not contain duplicates")
            dataset = self._dataset_repository.get_by_id(raw_id)
            if dataset is None:
                raise DatasetNotFoundError("Dataset '%s' was not found" % raw_id)
            if dataset.task_type and dataset.task_type != normalized_model_type:
                raise ProjectValidationError(
                    "Dataset '%s' task_type does not match project model_type" % raw_id
                )
            normalized_dataset_ids.append(raw_id)
            seen.add(raw_id)

        normalized_description = description.strip() if isinstance(description, str) else None
        if normalized_description == "":
            normalized_description = None

        normalized_epochs = self._normalize_optional_positive_int(epochs, "epochs")
        normalized_batch = self._normalize_optional_positive_int(batch, "batch")
        normalized_imgsz = self._normalize_optional_positive_int(imgsz, "imgsz")

        return {
            "project": normalized_project,
            "name": normalized_name,
            "model_type": normalized_model_type,
            "model_architecture": normalized_model_architecture,
            "description": normalized_description,
            "exp_root_path": normalized_exp_root_path,
            "dataset_ids": normalized_dataset_ids,
            "epochs": normalized_epochs,
            "batch": normalized_batch,
            "imgsz": normalized_imgsz,
        }

    def _normalize_optional_positive_int(
        self,
        value: Optional[int],
        field_name: str,
    ) -> Optional[int]:
        if value is None:
            return None
        if not isinstance(value, int):
            raise ProjectValidationError(
                "Project %s must be an integer when provided" % field_name
            )
        if value <= 0:
            raise ProjectValidationError(
                "Project %s must be greater than 0 when provided" % field_name
            )
        return value
