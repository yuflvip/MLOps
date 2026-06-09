from typing import Any, Dict, Mapping


def map_queue(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "id": payload.get("id"),
        "name": payload.get("name"),
        "tags": list(payload.get("tags") or []),
    }


def map_agent(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw_queues = payload.get("queues") or []
    queue_names = []
    for item in raw_queues:
        if isinstance(item, Mapping):
            queue_name = item.get("name") or item.get("id")
            if queue_name:
                queue_names.append(str(queue_name))
        elif item is not None:
            queue_names.append(str(item))

    raw_queue = payload.get("queue")
    if isinstance(raw_queue, Mapping):
        queue_value = raw_queue.get("name") or raw_queue.get("id")
    else:
        queue_value = raw_queue

    return {
        "id": payload.get("id"),
        "name": payload.get("name"),
        "queue": queue_value,
        "last_seen": payload.get("last_seen"),
        "status": payload.get("status") or "online",
        "queues": queue_names,
    }
