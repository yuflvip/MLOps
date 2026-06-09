from __future__ import annotations

import json
from pathlib import Path
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
    def __init__(
        self,
        api_base_url: str,
        access_key: str,
        secret_key: str,
        timeout_seconds: int = 30,
    ) -> None:
        self._api_base_url = api_base_url.rstrip("/")
        self._access_key = access_key
        self._secret_key = secret_key
        self._timeout_seconds = timeout_seconds
        self._bearer_token: str | None = None

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request_payload = self._build_task_create_request(payload)
        response = self._request("POST", "/tasks.create", json=request_payload)
        task_id = _extract_task_id(response)
        if not isinstance(task_id, str) or not task_id:
            raise RuntimeError("ClearML tasks.create did not return a task id")
        self._enqueue_task(task_id, request_payload.get("execution", {}).get("queue"))
        return {
            "id": task_id,
            "status": "queued",
            "payload": request_payload,
        }

    def list_queues(self) -> List[Dict[str, Any]]:
        response = self._request("POST", "/queues.get_all", json={})
        payload = self._extract_payload(response, "queues")
        return list(payload if isinstance(payload, list) else [])

    def list_agents(self) -> List[Dict[str, Any]]:
        response = self._request("POST", "/workers.get_all", json={})
        payload = self._extract_payload(response, "workers")
        return list(payload if isinstance(payload, list) else [])

    def _build_task_create_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = _normalize_mapping(payload.get("runtime"))
        execution_defaults = _normalize_mapping(payload.get("execution_defaults"))
        merged_runtime = dict(runtime)
        if execution_defaults:
            runtime_execution_params = _normalize_mapping(runtime.get("execution_params"))
            merged_execution_params = dict(execution_defaults)
            merged_execution_params.update(runtime_execution_params)
            merged_runtime["execution_params"] = merged_execution_params

        script_path = merged_runtime.get("script_path")
        if not isinstance(script_path, str) or not script_path:
            raise RuntimeError("Task runtime.script_path must be set")

        queue_name = payload.get("queue")
        queue_id = self._resolve_queue_id(queue_name)
        hyperparams = _build_hyperparams(
            args=_normalize_mapping(payload.get("parameters")),
            runtime=merged_runtime,
        )

        task_type = "testing" if payload.get("target_format") else "training"
        request_payload: Dict[str, Any] = {
            "name": str(payload["name"]),
            "type": task_type,
            "execution": {
                "queue": queue_id or queue_name,
            },
            "script": {
                "binary": "python",
                "entry_point": str(payload.get("entrypoint") or "generic_clearml_wrapper.py"),
                "working_dir": str(merged_runtime.get("working_dir") or ""),
                "diff": _load_wrapper_source(),
            },
            "hyperparams": hyperparams,
        }

        if payload.get("parent_clearml_task_id"):
            request_payload["parent"] = payload["parent_clearml_task_id"]
        if payload.get("project_id"):
            request_payload["project"] = payload["project_id"]
        if payload.get("comment"):
            request_payload["comment"] = payload["comment"]
        if payload.get("tags"):
            request_payload["tags"] = list(payload["tags"])
        return request_payload

    def _resolve_queue_id(self, queue_name: Any) -> str | None:
        if not isinstance(queue_name, str) or not queue_name:
            return None
        for queue in self.list_queues():
            if queue.get("name") == queue_name:
                queue_id = queue.get("id")
                if isinstance(queue_id, str) and queue_id:
                    return queue_id
        return None

    def _enqueue_task(self, task_id: str, queue_id: Any) -> None:
        enqueue_payload: Dict[str, Any] = {"task": task_id}
        if isinstance(queue_id, str) and queue_id:
            enqueue_payload["queue"] = queue_id
        self._request("POST", "/tasks.enqueue", json=enqueue_payload)

    def _ensure_bearer_token(self) -> str:
        if self._bearer_token:
            return self._bearer_token

        if not self._access_key or not self._secret_key:
            raise RuntimeError("ClearML access credentials are required")

        with httpx.Client(base_url=self._api_base_url, timeout=self._timeout_seconds) as client:
            response = client.get(
                "/auth.login",
                auth=(self._access_key, self._secret_key),
            )
            response.raise_for_status()
            payload = response.json()

        token = None
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, dict):
                token = data.get("token")

        if not isinstance(token, str) or not token:
            raise RuntimeError("ClearML auth.login did not return a bearer token")

        self._bearer_token = token
        return token

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {self._ensure_bearer_token()}"

        with httpx.Client(base_url=self._api_base_url, timeout=self._timeout_seconds) as client:
            response = client.request(method, path, headers=headers, **kwargs)
            if response.status_code == 401:
                self._bearer_token = None
                headers["Authorization"] = f"Bearer {self._ensure_bearer_token()}"
                response = client.request(method, path, headers=headers, **kwargs)
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


def _normalize_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                loaded = json.loads(value)
            except json.JSONDecodeError:
                return {}
            if isinstance(loaded, dict):
                return dict(loaded)
    return {}


def _build_hyperparams(
    args: Dict[str, Any],
    runtime: Dict[str, Any],
) -> Dict[str, Dict[str, Dict[str, str]]]:
    return {
        "Args": {
            key: {
                "name": key,
                "section": "Args",
                "type": _infer_hyperparam_type(value),
                "value": _serialize_hyperparam_value(value),
            }
            for key, value in sorted(args.items())
            if value is not None
        },
        "Runtime": {
            key: {
                "name": key,
                "section": "Runtime",
                "type": _infer_hyperparam_type(value),
                "value": _serialize_hyperparam_value(value),
            }
            for key, value in sorted(runtime.items())
            if value is not None
        },
    }


def _infer_hyperparam_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def _serialize_hyperparam_value(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _extract_task_id(response: Dict[str, Any]) -> str | None:
    if isinstance(response.get("id"), str):
        return response["id"]

    data = response.get("data")
    if isinstance(data, dict):
        if isinstance(data.get("id"), str):
            return data["id"]
        task = data.get("task")
        if isinstance(task, dict) and isinstance(task.get("id"), str):
            return task["id"]

    task = response.get("task")
    if isinstance(task, dict) and isinstance(task.get("id"), str):
        return task["id"]
    return None


def _load_wrapper_source() -> str:
    wrapper_path = Path(__file__).resolve().parents[3] / "scripts" / "generic_clearml_wrapper.py"
    if not wrapper_path.exists():
        raise FileNotFoundError(f"ClearML wrapper source not found: {wrapper_path}")
    return wrapper_path.read_text(encoding="utf-8")
