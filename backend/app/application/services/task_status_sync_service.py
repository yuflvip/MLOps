from typing import Any, Dict

from app.infrastructure.clearml.adapter import ClearMLAdapter
from app.infrastructure.repositories import TaskRepository


class TaskStatusSyncService:
    def __init__(
        self,
        clearml_adapter: ClearMLAdapter,
        task_repository: TaskRepository,
    ) -> None:
        self._clearml_adapter = clearml_adapter
        self._task_repository = task_repository

    def sync_pending_tasks(self, *, limit: int = 100) -> Dict[str, int]:
        tasks = self._task_repository.list_sync_candidates(limit=limit)
        clearml_task_ids = [
            task.clearml_task_id
            for task in tasks
            if isinstance(task.clearml_task_id, str) and task.clearml_task_id
        ]
        if not clearml_task_ids:
            return {"scanned": 0, "updated": 0, "missing": 0}

        remote_tasks = self._clearml_adapter.get_task_statuses(clearml_task_ids)
        remote_statuses = {
            task["id"]: task
            for task in remote_tasks
            if isinstance(task, dict) and isinstance(task.get("id"), str)
        }

        updated = 0
        missing = 0
        for task in tasks:
            clearml_task_id = task.clearml_task_id
            if not clearml_task_id:
                continue
            remote_task = remote_statuses.get(clearml_task_id)
            if remote_task is None:
                missing += 1
                task.last_sync_status = "missing"
                task.last_sync_error = (
                    "ClearML task '%s' was not returned by tasks.get_all"
                    % clearml_task_id
                )
                task.sync_version += 1
                self._task_repository.save(task)
                continue

            remote_status = remote_task.get("status")
            if isinstance(remote_status, str) and remote_status:
                task.status = remote_status
            task.last_sync_status = "success"
            task.last_sync_error = None
            task.sync_version += 1
            self._task_repository.save(task)
            updated += 1

        self._task_repository.commit()
        return {
            "scanned": len(clearml_task_ids),
            "updated": updated,
            "missing": missing,
        }
