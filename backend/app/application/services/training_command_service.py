import json
from typing import Any, Dict, List, Optional

from app.application.services.task_query_service import serialize_task
from app.application.services.template_service import TemplateService
from app.infrastructure.clearml.adapter import ClearMLAdapter
from app.infrastructure.db.models import TaskModel
from app.infrastructure.repositories import TaskRepository


class TrainingCommandService:
    def __init__(
        self,
        template_service: TemplateService,
        clearml_adapter: ClearMLAdapter,
        task_repository: TaskRepository,
    ) -> None:
        self._template_service = template_service
        self._clearml_adapter = clearml_adapter
        self._task_repository = task_repository

    def create_task(
        self,
        task_name: str,
        template_name: str,
        params: Optional[Dict[str, Any]] = None,
        execution_params: Optional[Dict[str, Any]] = None,
        queue_name: Optional[str] = None,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        template = self._template_service.get_template(template_name)
        resolved_queue_name = queue_name or template.get("queue")
        merged_params = dict(template.get("defaults", {}))
        if params:
            merged_params.update(params)

        payload = self._build_clearml_payload(
            task_name=task_name,
            template=template,
            queue_name=resolved_queue_name,
            parameters=merged_params,
            execution_params=execution_params or {},
        )
        warnings = self._build_queue_warnings(resolved_queue_name)
        clearml_task = self._clearml_adapter.create_task(payload)

        task = self._task_repository.add(
            TaskModel(
                task_name=task_name,
                task_group="training",
                task_type="training",
                task_source="platform",
                status=clearml_task.get("status", "queued"),
                clearml_task_id=_resolve_clearml_task_id(clearml_task),
                queue_name=resolved_queue_name,
                template_name=template_name,
                params_json=_dump_json(params or {}),
                parameter_snapshot_json=_dump_json(merged_params),
                runtime_snapshot_json=_dump_json(
                    {
                        "entrypoint": template.get("entrypoint"),
                        "queue_name": resolved_queue_name,
                        "execution_params": execution_params or {},
                    }
                ),
                custom_data_json=_dump_json(
                    {
                        "template": _extract_template_context(template),
                        "custom_data": custom_data or {},
                    }
                ),
                result_summary_json=_dump_json(clearml_task),
            )
        )
        self._task_repository.commit()

        return {
            "task": serialize_task(task),
            "warnings": warnings,
            "submission": _build_submission_summary(clearml_task),
        }

    def _build_clearml_payload(
        self,
        task_name: str,
        template: Dict[str, Any],
        queue_name: Optional[str],
        parameters: Dict[str, Any],
        execution_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = {
            "name": task_name,
            "template_name": template["name"],
            "queue": queue_name,
            "entrypoint": template.get("entrypoint"),
            "parameters": parameters,
        }
        project_value = parameters.get("project")
        if isinstance(project_value, str) and project_value:
            payload["project"] = project_value
        payload.update(_extract_template_context(template))
        runtime = dict(payload.get("runtime") or {})
        if execution_params:
            runtime["execution_params"] = dict(execution_params)
            payload["runtime"] = runtime
        return payload

    def _build_queue_warnings(self, queue_name: Optional[str]) -> List[str]:
        if not queue_name:
            return []
        for queue_status in self._clearml_adapter.list_queue_statuses():
            if queue_status["queue_name"] == queue_name:
                if queue_status["has_online_agents"]:
                    return []
                return [
                    "Queue '%s' has no online agents. The task will remain queued until an agent comes online."
                    % queue_name
                ]
        return []


def _extract_template_context(template: Dict[str, Any]) -> Dict[str, Any]:
    excluded_keys = {"name", "display_name", "queue", "entrypoint", "defaults"}
    return {
        key: value for key, value in template.items() if key not in excluded_keys
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
