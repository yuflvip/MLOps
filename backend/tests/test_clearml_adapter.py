from app.infrastructure.clearml.adapter import ClearMLAdapter


class StubClearMLClient:
    def create_task(self, payload):
        return {"id": "task-1", **payload}

    def list_queues(self):
        return [
            {"id": "q1", "name": "gpu-a", "tags": ["gpu"]},
            {"id": "q2", "name": "gpu-b", "tags": ["cpu"]},
        ]

    def list_agents(self):
        return [
            {
                "id": "a1",
                "name": "agent-1",
                "queue": "gpu-a",
                "status": "online",
                "last_seen": "2026-06-06T10:00:00Z",
            },
            {
                "id": "a2",
                "name": "agent-2",
                "queues": ["gpu-a", "gpu-b"],
                "status": "offline",
                "last_seen": "2026-06-06T09:00:00Z",
            },
        ]


def test_clearml_adapter_lists_queue_status_summaries():
    adapter = ClearMLAdapter(StubClearMLClient())

    summaries = adapter.list_queue_statuses()

    assert summaries == [
        {
            "queue_name": "gpu-a",
            "agent_count": 2,
            "has_online_agents": True,
            "last_seen": "2026-06-06T10:00:00Z",
            "agents": [
                {
                    "id": "a1",
                    "name": "agent-1",
                    "queue": "gpu-a",
                    "last_seen": "2026-06-06T10:00:00Z",
                    "status": "online",
                    "queues": [],
                },
                {
                    "id": "a2",
                    "name": "agent-2",
                    "queue": None,
                    "last_seen": "2026-06-06T09:00:00Z",
                    "status": "offline",
                    "queues": ["gpu-a", "gpu-b"],
                },
            ],
        },
        {
            "queue_name": "gpu-b",
            "agent_count": 1,
            "has_online_agents": False,
            "last_seen": "2026-06-06T09:00:00Z",
            "agents": [
                {
                    "id": "a2",
                    "name": "agent-2",
                    "queue": None,
                    "last_seen": "2026-06-06T09:00:00Z",
                    "status": "offline",
                    "queues": ["gpu-a", "gpu-b"],
                }
            ],
        },
    ]
