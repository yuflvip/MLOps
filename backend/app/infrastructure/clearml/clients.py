from typing import Any, Dict, List, Protocol

import httpx


class ClearMLClientProtocol(Protocol):
    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def list_queues(self) -> List[Dict[str, Any]]:
        ...

    def list_agents(self) -> List[Dict[str, Any]]:
        ...


class StubClearMLClient:
    def __init__(self) -> None:
        self._counter = 0

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._counter += 1
        return {
            "id": "local-clearml-%04d" % self._counter,
            "status": "queued",
            "payload": payload,
        }

    def list_queues(self) -> List[Dict[str, Any]]:
        return []

    def list_agents(self) -> List[Dict[str, Any]]:
        return []


class HttpClearMLClient:
    def __init__(self, api_base_url: str, timeout_seconds: int = 30) -> None:
        self._api_base_url = api_base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = self._request("POST", "/tasks", json=payload)
        return self._extract_payload(response, "task")

    def list_queues(self) -> List[Dict[str, Any]]:
        response = self._request("GET", "/queues")
        payload = self._extract_payload(response, "queues")
        return list(payload if isinstance(payload, list) else [])

    def list_agents(self) -> List[Dict[str, Any]]:
        response = self._request("GET", "/agents")
        payload = self._extract_payload(response, "agents")
        return list(payload if isinstance(payload, list) else [])

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        with httpx.Client(base_url=self._api_base_url, timeout=self._timeout_seconds) as client:
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            payload = response.json()
        return payload if isinstance(payload, dict) else {"data": payload}

    @staticmethod
    def _extract_payload(response: Dict[str, Any], key: str) -> Any:
        if key in response:
            return response[key]
        data = response.get("data")
        if isinstance(data, dict) and key in data:
            return data[key]
        return data if data is not None else response
