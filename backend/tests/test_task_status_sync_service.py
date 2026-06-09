from pathlib import Path

from app.application.services.task_status_sync_service import TaskStatusSyncService
from app.infrastructure.clearml.adapter import ClearMLAdapter
from app.infrastructure.db import Base, build_session_factory
from app.infrastructure.db.models import TaskModel
from app.infrastructure.repositories import TaskRepository


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class StubClearMLClient:
    def __init__(self):
        self.requested_task_ids = []

    def create_task(self, payload):
        return {"id": "unused", **payload}

    def list_queues(self):
        return []

    def list_agents(self):
        return []

    def get_tasks(self, task_ids):
        self.requested_task_ids.append(list(task_ids))
        return [
            {"id": "clearml-train-001", "status": "in_progress"},
            {"id": "clearml-train-002", "status": "completed"},
        ]


def test_task_status_sync_service_updates_non_terminal_tasks():
    session_factory = build_session_factory("sqlite+pysqlite:///:memory:")
    engine = session_factory.kw["bind"]
    Base.metadata.create_all(engine)

    client = StubClearMLClient()
    adapter = ClearMLAdapter(client)

    with session_factory() as session:
        repository = TaskRepository(session)
        repository.add(
            TaskModel(
                task_name="train-001",
                task_group="training",
                task_type="training",
                task_source="platform",
                status="queued",
                clearml_task_id="clearml-train-001",
            )
        )
        repository.add(
            TaskModel(
                task_name="train-002",
                task_group="training",
                task_type="training",
                task_source="platform",
                status="queued",
                clearml_task_id="clearml-train-002",
            )
        )
        repository.add(
            TaskModel(
                task_name="train-003",
                task_group="training",
                task_type="training",
                task_source="platform",
                status="completed",
                clearml_task_id="clearml-train-003",
            )
        )
        session.commit()

        service = TaskStatusSyncService(
            clearml_adapter=adapter,
            task_repository=repository,
        )

        result = service.sync_pending_tasks(limit=50)
        session.commit()

        first = repository.get_by_clearml_task_id("clearml-train-001")
        second = repository.get_by_clearml_task_id("clearml-train-002")
        third = repository.get_by_clearml_task_id("clearml-train-003")

    assert result == {
        "scanned": 2,
        "updated": 2,
        "missing": 0,
    }
    assert client.requested_task_ids == [["clearml-train-001", "clearml-train-002"]]
    assert first is not None
    assert first.status == "in_progress"
    assert first.last_sync_status == "success"
    assert first.last_sync_error is None
    assert first.sync_version == 2
    assert second is not None
    assert second.status == "completed"
    assert second.last_sync_status == "success"
    assert second.last_sync_error is None
    assert second.sync_version == 2
    assert third is not None
    assert third.status == "completed"
    assert third.last_sync_status is None
    assert third.sync_version == 1
