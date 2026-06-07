from typing import Any, Dict, Mapping


def map_queue(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "id": payload.get("id"),
        "name": payload.get("name"),
        "tags": list(payload.get("tags") or []),
    }


def map_agent(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "id": payload.get("id"),
        "name": payload.get("name"),
        "queue": payload.get("queue"),
        "last_seen": payload.get("last_seen"),
        "status": payload.get("status"),
        "queues": list(payload.get("queues") or []),
    }
