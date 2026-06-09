from typing import Any, Dict, List

from app.domain.common.exceptions import ClearMLAdapterError
from app.infrastructure.clearml.clients import ClearMLClientProtocol
from app.infrastructure.clearml.mapper import map_agent, map_queue
from app.infrastructure.clearml.queue_probe import build_queue_status_summary


class ClearMLAdapter:
    def __init__(self, client: ClearMLClientProtocol):
        self._client = client

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not payload:
            raise ClearMLAdapterError("ClearML task payload must not be empty")
        try:
            return self._client.create_task(payload)
        except Exception as exc:
            raise ClearMLAdapterError(
                "Failed to create task in ClearML: %s" % exc
            ) from exc

    def list_queues(self) -> List[Dict[str, Any]]:
        try:
            return [map_queue(item) for item in self._client.list_queues()]
        except Exception as exc:
            raise ClearMLAdapterError(
                "Failed to fetch queue metadata from ClearML: %s" % exc
            ) from exc

    def list_agents(self) -> List[Dict[str, Any]]:
        try:
            return [map_agent(item) for item in self._client.list_agents()]
        except Exception as exc:
            raise ClearMLAdapterError(
                "Failed to fetch agent metadata from ClearML: %s" % exc
            ) from exc

    def list_queue_statuses(self) -> List[Dict[str, Any]]:
        queues = self.list_queues()
        agents = self.list_agents()
        return [build_queue_status_summary(queue, agents) for queue in queues]

    def get_task_statuses(self, task_ids: List[str]) -> List[Dict[str, Any]]:
        try:
            return list(self._client.get_tasks(task_ids))
        except Exception as exc:
            raise ClearMLAdapterError(
                "Failed to fetch task statuses from ClearML: %s" % exc
            ) from exc

    def get_task_log(
        self,
        task: str,
        batch_size: int = 500,
        from_timestamp: int | None = None,
        order: str = "asc",
    ) -> Dict[str, Any]:
        try:
            return self._client.get_task_log(
                task=task,
                batch_size=batch_size,
                from_timestamp=from_timestamp,
                order=order,
            )
        except Exception as exc:
            raise ClearMLAdapterError(
                "Failed to fetch task log from ClearML: %s" % exc
            ) from exc
