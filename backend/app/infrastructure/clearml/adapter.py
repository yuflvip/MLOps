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
        return self._client.create_task(payload)

    def list_queues(self) -> List[Dict[str, Any]]:
        return [map_queue(item) for item in self._client.list_queues()]

    def list_agents(self) -> List[Dict[str, Any]]:
        return [map_agent(item) for item in self._client.list_agents()]

    def list_queue_statuses(self) -> List[Dict[str, Any]]:
        queues = self.list_queues()
        agents = self.list_agents()
        return [build_queue_status_summary(queue, agents) for queue in queues]
