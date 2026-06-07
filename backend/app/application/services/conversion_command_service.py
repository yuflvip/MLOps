import json
from typing import Any, Dict, Optional

from app.application.services.task_query_service import serialize_task
from app.application.services.template_service import TemplateService
from app.domain.common.exceptions import DomainError
from app.infrastructure.clearml.adapter import ClearMLAdapter
from app.infrastructure.db.models import TaskModel
from app.infrastructure.repositories import TaskRepository


class ConversionCommandService:
    def __init__(
        self,
        template_service: TemplateService,
        clearml_adapter: ClearMLAdapter,
        task_repository: TaskRepository,
        template_name: str = "pt-to-onnx-default",
    ) -> None:
        self._template_service = template_service
        self._clearml_adapter = clearml_adapter
        self._task_repository = task_repository
        self._template_name = template_name

    def create_export_onnx_task(
        self,
        parent_task_id: int,
        task_name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        parent_task = self._task_repository.get_by_id(parent_task_id)
        if parent_task is None:
            raise DomainError("Parent training task '%s' was not found" % parent_task_id)
        if not _is_training_task(parent_task):
            raise DomainError(
                "Parent task '%s' is not a training task" % parent_task_id
            )

        resolved_task_name = task_name or "%s-export-onnx" % parent_task.task_name
        template = self._template_service.get_template(self._template_name)
        merged_params = dict(template.get("defaults", {}))
        if params:
            merged_params.update(params)

        payload = {
            "name": resolved_task_name,
            "parent_task_id": parent_task.id,
            "parent_clearml_task_id": parent_task.clearml_task_id,
            "queue": parent_task.queue_name,
            "source_task_type": parent_task.task_type,
            "target_format": "onnx",
            "template_name": template["name"],
            "parameters": merged_params,
        }
        payload.update(_extract_template_context(template))
        clearml_task = self._clearml_adapter.create_task(payload)

        task = self._task_repository.add(
            TaskModel(
                task_name=resolved_task_name,
                parent_task_id=parent_task.id,
                task_group="export",
                task_type="export_onnx",
                task_source="platform",
                status=clearml_task.get("status", "queued"),
                clearml_task_id=_resolve_clearml_task_id(clearml_task),
                queue_name=parent_task.queue_name,
                template_name=template["name"],
                params_json=_dump_json(params or {}),
                parameter_snapshot_json=_dump_json(merged_params),
                runtime_snapshot_json=_dump_json(
                    {
                        "parent_clearml_task_id": parent_task.clearml_task_id,
                        "target_format": "onnx",
                    }
                ),
                custom_data_json=_dump_json(
                    {
                        "source_task_id": parent_task.id,
                        "source_clearml_task_id": parent_task.clearml_task_id,
                        "template": _extract_template_context(template),
                    }
                ),
                result_summary_json=_dump_json(clearml_task),
            )
        )
        self._task_repository.commit()

        return {
            "task": serialize_task(task),
            "warnings": [],
            "submission": _build_submission_summary(clearml_task),
        }


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _resolve_clearml_task_id(clearml_task: Dict[str, Any]) -> Optional[str]:
    return (
        clearml_task.get("id")
        or clearml_task.get("task_id")
        or clearml_task.get("clearml_task_id")
    )


def _build_submission_summary(clearml_task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "clearml_task_id": _resolve_clearml_task_id(clearml_task),
        "status": clearml_task.get("status"),
    }


def _extract_template_context(template: Dict[str, Any]) -> Dict[str, Any]:
    excluded_keys = {"name", "display_name", "defaults"}
    return {
        key: value for key, value in template.items() if key not in excluded_keys
    }


def _is_training_task(task: TaskModel) -> bool:
    return task.task_group == "training" and task.task_type == "training"
