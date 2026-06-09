from pathlib import Path

import pytest

from app.application.services.conversion_command_service import (
    ConversionCommandService,
)
from app.application.services.task_query_service import TaskQueryService
from app.application.services.template_service import TemplateService
from app.application.services.training_command_service import (
    TrainingCommandService,
)
from app.domain.common.exceptions import DomainError
from app.infrastructure.clearml.adapter import ClearMLAdapter
from app.infrastructure.db import Base, build_session_factory
from app.infrastructure.db.models import TaskModel
from app.infrastructure.repositories import TaskRepository


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class StubClearMLClient:
    def __init__(self):
        self.created_payloads = []

    def create_task(self, payload):
        self.created_payloads.append(payload)
        return {
            "id": "clearml-%02d" % len(self.created_payloads),
            "status": "queued",
            "payload": payload,
        }

    def list_queues(self):
        return [
            {"id": "q1", "name": "queue_train_gpu"},
            {"id": "q2", "name": "training-default"},
        ]

    def list_agents(self):
        return [
            {
                "id": "agent-1",
                "name": "offline-agent",
                "queue": "queue_train_gpu",
                "status": "offline",
                "last_seen": "2026-06-06T08:00:00Z",
            }
        ]


def build_services():
    session_factory = build_session_factory("sqlite+pysqlite:///:memory:")
    engine = session_factory.kw["bind"]
    Base.metadata.create_all(engine)

    session = session_factory()
    repository = TaskRepository(session)
    training_template_service = TemplateService(
        BACKEND_ROOT / "config" / "training-templates.yaml"
    )
    conversion_template_service = TemplateService(
        BACKEND_ROOT / "config" / "conversion-templates.yaml"
    )
    clearml_client = StubClearMLClient()
    clearml_adapter = ClearMLAdapter(clearml_client)

    return (
        session,
        repository,
        training_template_service,
        conversion_template_service,
        clearml_adapter,
        clearml_client,
    )


def test_training_command_service_returns_warning_when_queue_has_no_online_agents():
    (
        session,
        repository,
        training_template_service,
        _conversion_template_service,
        clearml_adapter,
        clearml_client,
    ) = build_services()
    service = TrainingCommandService(
        template_service=training_template_service,
        clearml_adapter=clearml_adapter,
        task_repository=repository,
    )

    result = service.create_task(
        task_name="train-yolo-a",
        template_name="yolo-default",
        params={"epochs": 5},
    )

    session.close()

    assert result["warnings"] == [
        "Queue 'queue_train_gpu' has no online agents. The task will remain queued until an agent comes online."
    ]
    assert result["task"]["template_name"] == "yolo-default"
    assert result["task"]["clearml_task_id"] == "clearml-01"
    assert result["submission"] == {
        "clearml_task_id": "clearml-01",
        "status": "queued",
    }
    assert "clearml_task" not in result
    assert clearml_client.created_payloads[0]["template_name"] == "yolo-default"
    assert clearml_client.created_payloads[0]["queue"] == "queue_train_gpu"
    assert clearml_client.created_payloads[0]["parameters"]["epochs"] == 5
    assert clearml_client.created_payloads[0]["entrypoint"] == "generic_clearml_wrapper.py"
    assert clearml_client.created_payloads[0]["runtime"]["script_path"] == "train.py"
    assert clearml_client.created_payloads[0]["execution_defaults"] == {
        "nproc_per_node": 1,
    }


def test_training_command_service_propagates_convnext_runtime_context():
    (
        session,
        repository,
        training_template_service,
        _conversion_template_service,
        clearml_adapter,
        clearml_client,
    ) = build_services()
    service = TrainingCommandService(
        template_service=training_template_service,
        clearml_adapter=clearml_adapter,
        task_repository=repository,
    )

    result = service.create_task(
        task_name="train-convnext-a",
        template_name="convnext-default",
    )

    session.close()

    assert result["task"]["template_name"] == "convnext-default"
    assert clearml_client.created_payloads[0]["entrypoint"] == "generic_clearml_wrapper.py"
    assert clearml_client.created_payloads[0]["queue"] == "train_convnext"
    assert clearml_client.created_payloads[0]["runtime"]["script_path"] == (
        "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls/tools/train.py"
    )
    assert clearml_client.created_payloads[0]["execution_defaults"] == {
        "cuda_visible_devices": "2",
        "nproc_per_node": 1,
    }
    assert clearml_client.created_payloads[0]["parameters"] == {
        "batch": 64,
        "data": "/mnt/imgs_coco_datasets_145/2026_imgs_datasets/imgs_cls_vehicle_10class/imgs_cls_vehicle_10class_baseline/",
        "epochs": 1,
        "imgsz": 224,
        "project": "classify_vehicle_10class",
    }


def test_conversion_command_service_creates_export_child_task():
    (
        session,
        repository,
        training_template_service,
        conversion_template_service,
        clearml_adapter,
        clearml_client,
    ) = build_services()
    training_service = TrainingCommandService(
        template_service=training_template_service,
        clearml_adapter=clearml_adapter,
        task_repository=repository,
    )
    conversion_service = ConversionCommandService(
        template_service=conversion_template_service,
        clearml_adapter=clearml_adapter,
        task_repository=repository,
    )

    training_result = training_service.create_task(
        task_name="train-yolo-b",
        template_name="yolo-default",
        params={"epochs": 10},
    )
    export_result = conversion_service.create_export_onnx_task(
        parent_task_id=training_result["task"]["id"],
        params={"opset": 18, "dynamic": True},
    )

    session.close()

    assert export_result["task"]["task_type"] == "export_onnx"
    assert export_result["task"]["parent_task_id"] == training_result["task"]["id"]
    assert export_result["task"]["template_name"] == "pt-to-onnx-default"
    assert export_result["submission"] == {
        "clearml_task_id": "clearml-02",
        "status": "queued",
    }
    assert "clearml_task" not in export_result
    assert clearml_client.created_payloads[1]["target_format"] == "onnx"
    assert clearml_client.created_payloads[1]["parameters"]["opset"] == 18
    assert clearml_client.created_payloads[1]["parameters"]["dynamic"] is True


def test_conversion_command_service_uses_template_defaults():
    (
        session,
        repository,
        training_template_service,
        conversion_template_service,
        clearml_adapter,
        clearml_client,
    ) = build_services()
    training_service = TrainingCommandService(
        template_service=training_template_service,
        clearml_adapter=clearml_adapter,
        task_repository=repository,
    )
    conversion_service = ConversionCommandService(
        template_service=conversion_template_service,
        clearml_adapter=clearml_adapter,
        task_repository=repository,
    )

    training_result = training_service.create_task(
        task_name="train-yolo-default-export",
        template_name="yolo-default",
    )
    export_result = conversion_service.create_export_onnx_task(
        parent_task_id=training_result["task"]["id"]
    )

    session.close()

    assert export_result["task"]["parameter_snapshot"] == {
        "dynamic": False,
        "opset": 17,
    }
    assert clearml_client.created_payloads[1]["parameters"] == {
        "dynamic": False,
        "opset": 17,
    }


def test_conversion_command_service_rejects_non_training_parent_task():
    (
        session,
        repository,
        _training_template_service,
        conversion_template_service,
        clearml_adapter,
        _clearml_client,
    ) = build_services()
    repository.add(
        TaskModel(
            task_name="not-training",
            task_group="export",
            task_type="export_onnx",
            task_source="platform",
            status="queued",
            clearml_task_id="existing-export-01",
        )
    )
    repository.commit()
    export_parent = repository.get_by_clearml_task_id("existing-export-01")
    conversion_service = ConversionCommandService(
        template_service=conversion_template_service,
        clearml_adapter=clearml_adapter,
        task_repository=repository,
    )

    with pytest.raises(DomainError, match="is not a training task"):
        conversion_service.create_export_onnx_task(parent_task_id=export_parent.id)

    session.close()


def test_task_query_service_lists_and_reads_task_details():
    (
        session,
        repository,
        training_template_service,
        _conversion_template_service,
        clearml_adapter,
        _clearml_client,
    ) = build_services()
    training_service = TrainingCommandService(
        template_service=training_template_service,
        clearml_adapter=clearml_adapter,
        task_repository=repository,
    )
    query_service = TaskQueryService(task_repository=repository)

    training_result = training_service.create_task(
        task_name="train-yolo-c",
        template_name="default-training",
        params={"batch_size": 8},
    )
    list_result = query_service.list_tasks(task_group="training")
    detail_result = query_service.get_task_detail(training_result["task"]["id"])

    session.close()

    assert list_result["total"] == 1
    assert list_result["items"][0]["task_name"] == "train-yolo-c"
    assert detail_result is not None
    assert detail_result["template_name"] == "default-training"
