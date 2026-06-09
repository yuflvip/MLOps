import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routers import (
    get_clearml_adapter,
    get_conversion_command_service,
    get_scheduler_service,
    get_task_query_service,
    get_template_service,
    get_training_command_service,
)
from app.main import create_app


class SmokeTaskQueryService:
    def list_tasks(self, **_kwargs):
        return {
            "items": [
                {
                    "id": 1,
                    "task_name": "train-smoke",
                    "task_group": "training",
                    "task_type": "training",
                    "status": "completed",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }

    def get_task_detail(self, task_id):
        if task_id != 1:
            return None
        return {
            "id": 1,
            "task_name": "train-smoke",
            "task_group": "training",
            "task_type": "training",
            "status": "completed",
        }


class SmokeTemplateService:
    def list_templates(self):
        return [
            {
                "name": "yolo-default",
                "display_name": "YOLO Default",
                "queue": "queue_train_gpu",
                "entrypoint": "python train.py",
                "defaults": {"epochs": 100},
                "execution_defaults": {"nproc_per_node": 1},
            }
        ]


class SmokeClearMLAdapter:
    def list_queue_statuses(self):
        return [
            {
                "queue_name": "queue_train_gpu",
                "agent_count": 1,
                "has_online_agents": True,
                "agents": [{"name": "agent-1", "status": "online"}],
                "last_seen": "2026-06-08T00:00:00Z",
            }
        ]


class SmokeSchedulerService:
    def get_runtime_status(self):
        return {
            "scheduler": {
                "enabled": True,
                "running": True,
                "job_count": 1,
            }
        }


class SmokeTrainingCommandService:
    def create_task(self, **_kwargs):
        return {
            "task": {
                "id": 2,
                "parent_task_id": None,
                "task_name": "train-created",
                "task_group": "training",
                "task_type": "training",
                "status": "queued",
                "clearml_task_id": "clearml-train-002",
            },
            "warnings": [],
            "submission": {
                "clearml_task_id": "clearml-train-002",
                "status": "queued",
            },
        }


class SmokeConversionCommandService:
    def create_export_onnx_task(self, **_kwargs):
        return {
            "task": {
                "id": 3,
                "parent_task_id": 1,
                "task_name": "train-smoke-export-onnx",
                "task_group": "export",
                "task_type": "export_onnx",
                "status": "queued",
                "clearml_task_id": "clearml-export-003",
            },
            "warnings": [],
            "submission": {
                "clearml_task_id": "clearml-export-003",
                "status": "queued",
            },
        }


def build_smoke_app():
    app = create_app()
    assert app.state.container.settings.clearml.api_base_url == "http://192.168.1.155:8008"

    async def override_task_query_service():
        return SmokeTaskQueryService()

    async def override_template_service():
        return SmokeTemplateService()

    async def override_clearml_adapter():
        return SmokeClearMLAdapter()

    async def override_scheduler_service():
        return SmokeSchedulerService()

    async def override_training_command_service():
        return SmokeTrainingCommandService()

    async def override_conversion_command_service():
        return SmokeConversionCommandService()

    app.dependency_overrides[get_task_query_service] = override_task_query_service
    app.dependency_overrides[get_template_service] = override_template_service
    app.dependency_overrides[get_clearml_adapter] = override_clearml_adapter
    app.dependency_overrides[get_scheduler_service] = override_scheduler_service
    app.dependency_overrides[get_training_command_service] = (
        override_training_command_service
    )
    app.dependency_overrides[get_conversion_command_service] = (
        override_conversion_command_service
    )
    return app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_and_runtime_smoke():
    app = build_smoke_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        health_response = await client.get("/mlops/system/health")
        runtime_response = await client.get("/mlops/system/runtime")

    assert health_response.status_code == 200
    health_payload = health_response.json()
    assert health_payload["code"] == 0
    assert health_payload["message"] == "success"
    assert health_payload["warnings"] == []
    assert health_payload["data"]["status"] == "ok"
    assert health_payload["data"]["app_name"] == "mlops-backend"

    assert runtime_response.status_code == 200
    runtime_payload = runtime_response.json()
    assert runtime_payload["code"] == 0
    assert runtime_payload["warnings"] == []
    assert runtime_payload["data"]["scheduler"]["enabled"] is True
    assert runtime_payload["data"]["scheduler"]["running"] is True
    assert runtime_payload["data"]["scheduler"]["job_count"] == 1


@pytest.mark.anyio
async def test_training_and_conversion_smoke_flow():
    app = build_smoke_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_meta_response = await client.get("/mlops/training/create-meta")
        list_response = await client.get("/mlops/training")
        detail_response = await client.get("/mlops/training/1")
        create_training_response = await client.post(
            "/mlops/training",
            json={
                "task_name": "train-created",
                "template_name": "yolo-default",
                "params": {"epochs": 10},
                "execution_params": {
                    "nproc_per_node": 2,
                    "cuda_visible_devices": "1",
                },
                "queue_name": "queue_train_gpu",
                "custom_data": {"source": "smoke"},
            },
        )
        conversion_response = await client.post(
            "/mlops/conversion/onnx",
            json={
                "parent_task_id": 1,
                "task_name": "train-smoke-export-onnx",
                "params": {"opset": 17},
                "execution_params": {"nproc_per_node": 1},
            },
        )

    assert create_meta_response.status_code == 200
    create_meta_payload = create_meta_response.json()
    assert create_meta_payload["warnings"] == []
    assert create_meta_payload["data"]["templates"][0]["name"] == "yolo-default"
    assert create_meta_payload["data"]["queues"][0]["queue_name"] == "queue_train_gpu"

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["task_name"] == "train-smoke"

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["data"]["task_name"] == "train-smoke"
    assert detail_payload["data"]["task_group"] == "training"

    assert create_training_response.status_code == 200
    create_training_payload = create_training_response.json()
    assert create_training_payload["warnings"] == []
    assert create_training_payload["data"]["task"]["task_name"] == "train-created"
    assert create_training_payload["data"]["task"]["clearml_task_id"] == "clearml-train-002"
    assert create_training_payload["data"]["submission"]["status"] == "queued"

    assert conversion_response.status_code == 200
    conversion_payload = conversion_response.json()
    assert conversion_payload["warnings"] == []
    assert conversion_payload["data"]["task"]["task_type"] == "export_onnx"
    assert conversion_payload["data"]["task"]["parent_task_id"] == 1
    assert conversion_payload["data"]["submission"]["clearml_task_id"] == "clearml-export-003"
