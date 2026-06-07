from app.infrastructure.db import Base, build_session_factory
from app.infrastructure.db.models import TaskArtifactModel, TaskModel
from app.infrastructure.repositories import TaskRepository


def test_task_model_defaults_and_repository_add():
    session_factory = build_session_factory("sqlite+pysqlite:///:memory:")
    engine = session_factory.kw["bind"]
    Base.metadata.create_all(engine)

    with session_factory() as session:
        repository = TaskRepository(session)
        task = TaskModel(
            task_name="demo",
            task_group="training",
            task_type="training",
            task_source="platform",
            status="queued",
            queue_name="queue_train_gpu",
            template_name="yolo-default",
            params_json='{"epochs": 10}',
        )

        repository.add(task)
        session.commit()

        assert task.id is not None
        assert task.task_group == "training"
        assert task.status == "queued"
        assert task.sync_version == 1
        assert task.parameter_snapshot_json is None
        assert task.runtime_snapshot_json is None
        assert task.custom_data_json is None
        assert task.result_summary_json is None
        assert task.last_sync_status is None
        assert task.last_sync_error is None
        assert task.created_at is not None
        assert task.updated_at is not None


def test_task_repository_supports_lookup_filters_and_parent_child_queries():
    session_factory = build_session_factory("sqlite+pysqlite:///:memory:")
    engine = session_factory.kw["bind"]
    Base.metadata.create_all(engine)

    with session_factory() as session:
        repository = TaskRepository(session)
        parent_task = repository.add(
            TaskModel(
                task_name="train-001",
                task_group="training",
                task_type="training",
                task_source="platform",
                status="completed",
                clearml_task_id="clearml-train-001",
            )
        )
        child_task = repository.add(
            TaskModel(
                task_name="export-001",
                task_group="export",
                task_type="export_onnx",
                task_source="platform",
                status="queued",
                clearml_task_id="clearml-export-001",
                parent_task_id=parent_task.id,
            )
        )
        repository.add(
            TaskModel(
                task_name="train-002",
                task_group="training",
                task_type="training",
                task_source="sync",
                status="queued",
                clearml_task_id="clearml-train-002",
            )
        )
        session.commit()

        fetched_by_id = repository.get_by_id(parent_task.id)
        fetched_by_clearml = repository.get_by_clearml_task_id("clearml-export-001")
        children = repository.list_by_parent_task_id(parent_task.id)
        filtered_items, filtered_total = repository.list_paginated(
            page=1,
            page_size=10,
            task_group="training",
            task_type="training",
            status="queued",
        )
        child_task.status = "completed"
        saved_child_task = repository.save(child_task)
        session.commit()

        assert fetched_by_id is not None
        assert fetched_by_id.task_name == "train-001"
        assert fetched_by_clearml is not None
        assert fetched_by_clearml.id == child_task.id
        assert len(children) == 1
        assert children[0].id == child_task.id
        assert filtered_total == 1
        assert len(filtered_items) == 1
        assert filtered_items[0].clearml_task_id == "clearml-train-002"
        assert saved_child_task.status == "completed"


def test_task_and_artifact_relationships_support_parent_child_navigation():
    session_factory = build_session_factory("sqlite+pysqlite:///:memory:")
    engine = session_factory.kw["bind"]
    Base.metadata.create_all(engine)

    with session_factory() as session:
        repository = TaskRepository(session)
        parent_task = repository.add(
            TaskModel(
                task_name="train-parent",
                task_group="training",
                task_type="training",
                task_source="platform",
                status="completed",
            )
        )
        child_task = repository.add(
            TaskModel(
                task_name="export-child",
                task_group="export",
                task_type="export_onnx",
                task_source="platform",
                status="completed",
                parent=parent_task,
            )
        )
        parent_artifact = TaskArtifactModel(
            task_id=parent_task.id,
            artifact_role="model_weight",
            artifact_name="best.pt",
            format="pt",
        )
        child_artifact = TaskArtifactModel(
            task_id=child_task.id,
            artifact_role="model_export",
            artifact_name="best.onnx",
            format="onnx",
            parent=parent_artifact,
        )
        session.add(parent_artifact)
        session.add(child_artifact)
        session.commit()
        session.refresh(parent_task)
        session.refresh(child_task)
        session.refresh(parent_artifact)

        assert child_task.parent is not None
        assert child_task.parent.id == parent_task.id
        assert len(parent_task.children) == 1
        assert parent_task.children[0].id == child_task.id
        assert child_artifact.parent is not None
        assert child_artifact.parent.id == parent_artifact.id
        assert len(parent_artifact.children) == 1
        assert parent_artifact.children[0].artifact_name == "best.onnx"
