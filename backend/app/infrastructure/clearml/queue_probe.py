from typing import Any, Dict, Iterable, List, Optional


def summarize_queue_agents(queue_name: str, agents: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    queue_agents: List[Dict[str, Any]] = []
    for agent in agents:
        if agent.get("queue") == queue_name or queue_name in list(agent.get("queues") or []):
            queue_agents.append(agent)
    return {
        "queue_name": queue_name,
        "agent_count": len(queue_agents),
        "has_online_agents": any(agent.get("status") == "online" for agent in queue_agents),
        "agents": queue_agents,
        "last_seen": _latest_last_seen(queue_agents),
    }


def build_queue_status_summary(
    queue: Dict[str, Any], agents: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    summary = summarize_queue_agents(str(queue.get("name") or ""), agents)
    summary["queue_name"] = queue.get("name")
    return summary


def _latest_last_seen(agents: Iterable[Dict[str, Any]]) -> Optional[str]:
    last_seen_values = [agent.get("last_seen") for agent in agents if agent.get("last_seen")]
    if not last_seen_values:
        return None
    return max(last_seen_values)
