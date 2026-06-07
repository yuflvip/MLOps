import json
from typing import Any, Dict, List, Optional

from app.infrastructure.db.models import TaskModel
from app.infrastructure.repositories import TaskRepository


def serialize_task(task: TaskModel) -> Dict[str, Any]:
    return {
        "id": task.id,
        "parent_task_id": task.parent_task_id,
        "task_name": task.task_name,
        "task_group": task.task_group,
        "task_type": task.task_type,
        "task_source": task.task_source,
        "status": task.status,
        "clearml_task_id": task.clearml_task_id,
        "queue_name": task.queue_name,
        "template_name": task.template_name,
        "params": _load_json(task.params_json),
        "parameter_snapshot": _load_json(task.parameter_snapshot_json),
        "runtime_snapshot": _load_json(task.runtime_snapshot_json),
        "custom_data": _load_json(task.custom_data_json),
        "result_summary": _load_json(task.result_summary_json),
        "error_message": task.error_message,
        "last_sync_status": task.last_sync_status,
        "last_sync_error": task.last_sync_error,
        "sync_version": task.sync_version,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def _load_json(raw_value: Optional[str]) -> Any:
    if raw_value is None:
        return None
    return json.loads(raw_value)


class TaskQueryService:
    def __init__(self, task_repository: TaskRepository) -> None:
        self._task_repository = task_repository

    def list_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        task_group: Optional[str] = None,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        items, total = self._task_repository.list_paginated(
            page=page,
            page_size=page_size,
            task_group=task_group,
            task_type=task_type,
            status=status,
        )
        return {
            "items": [serialize_task(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_task_detail(self, task_id: int) -> Optional[Dict[str, Any]]:
        task = self._task_repository.get_by_id(task_id)
        if task is None:
            return None
        return serialize_task(task)

    def list_child_tasks(self, parent_task_id: int) -> List[Dict[str, Any]]:
        return [
            serialize_task(task)
            for task in self._task_repository.list_by_parent_task_id(parent_task_id)
        ]
