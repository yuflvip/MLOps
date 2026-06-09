from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class StubTaskQueryService:
    def list_tasks(self, **_kwargs):
        return {
            "items": [
                {
                    "id": 1,
                    "task_name": "train-demo",
                    "task_group": "training",
                    "task_type": "training",
                    "status": "queued",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }

    def get_task_detail(self, task_id):
        return {
            "id": task_id,
            "task_name": "train-demo",
            "task_group": "training",
            "task_type": "training",
            "status": "queued",
        }


class StubTrainingCommandService:
    last_payload = None

    def create_task(self, **_kwargs):
        self.last_payload = dict(_kwargs)
        return {
            "task": {
                "id": 2,
                "task_name": "train-created",
                "task_group": "training",
                "task_type": "training",
                "status": "queued",
            },
            "warnings": [],
            "submission": {
                "clearml_task_id": "clearml-02",
                "status": "queued",
            },
            "warnings": [
                "Queue 'queue_train_gpu' has no online agents. The task will remain queued until an agent comes online."
            ],
        }


class StubConversionCommandService:
    def create_export_onnx_task(self, **_kwargs):
        return {
            "task": {
                "id": 3,
                "parent_task_id": 1,
                "task_name": "train-demo-export-onnx",
                "task_group": "export",
                "task_type": "export_onnx",
                "status": "queued",
            },
            "warnings": [],
            "submission": {
                "clearml_task_id": "clearml-03",
                "status": "queued",
            },
        }


class StubTemplateService:
    def list_templates(self):
        return [
            {
                "name": "yolo-default",
                "display_name": "YOLO Default",
                "queue": "queue_train_gpu",
                "entrypoint": "python train.py",
                "defaults": {"epochs": 100},
                "runtime": {
                    "launcher": "python",
                    "script_path": "train.py",
                    "working_dir": "/workspace/yolo",
                    "env": {"CUDA_VISIBLE_DEVICES": "0"},
                    "artifacts": [
                        {
                            "name": "best_model",
                            "role": "model_weight",
                            "format": "pt",
                            "path": "{output_dir}/best.pt",
                        }
                    ],
                },
                "execution_defaults": {"nproc_per_node": 1},
            }
        ]


class StubClearMLAdapter:
    def list_queue_statuses(self):
        return [
            {
                "queue_name": "queue_train_gpu",
                "agent_count": 1,
                "has_online_agents": True,
                "agents": [{"name": "agent-1", "status": "online"}],
                "last_seen": "2026-06-06T08:00:00Z",
            }
        ]


class FailingClearMLAdapter:
    def list_queue_statuses(self):
        raise RuntimeError("clearml unavailable")


@pytest.fixture
def anyio_backend():
    return "asyncio"


def build_test_client():
    from app.api.routers import (
        get_clearml_adapter,
        get_conversion_command_service,
        get_task_query_service,
        get_template_service,
        get_training_command_service,
    )

    app = create_app(config_path=BACKEND_ROOT / "config" / "app.yaml")
    async def override_task_query_service():
        return StubTaskQueryService()

    async def override_training_command_service():
        return StubTrainingCommandService()

    async def override_conversion_command_service():
        return StubConversionCommandService()

    async def override_template_service():
        return StubTemplateService()

    async def override_clearml_adapter():
        return StubClearMLAdapter()

    app.dependency_overrides[get_task_query_service] = override_task_query_service
    app.dependency_overrides[get_training_command_service] = (
        override_training_command_service
    )
    app.dependency_overrides[get_conversion_command_service] = (
        override_conversion_command_service
    )
    app.dependency_overrides[get_template_service] = override_template_service
    app.dependency_overrides[get_clearml_adapter] = override_clearml_adapter
    return app


@pytest.mark.anyio
async def test_training_list_returns_unified_response_envelope():
    app = build_test_client()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/mlops/training")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"code", "message", "data", "request_id", "warnings"}
    assert payload["code"] == 0
    assert payload["message"] == "success"
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["task_name"] == "train-demo"
    assert payload["warnings"] == []
    assert payload["request_id"]


@pytest.mark.anyio
async def test_system_health_route_is_registered():
    app = build_test_client()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/mlops/system/health")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


@pytest.mark.anyio
async def test_training_create_meta_returns_queue_schema():
    app = build_test_client()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/mlops/training/create-meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["warnings"] == []
    assert payload["data"]["templates"][0]["name"] == "yolo-default"
    assert payload["data"]["templates"][0]["runtime"] == {
        "launcher": "python",
        "script_path": "train.py",
        "working_dir": "/workspace/yolo",
        "env": {"CUDA_VISIBLE_DEVICES": "0"},
        "artifacts": [
            {
                "name": "best_model",
                "role": "model_weight",
                "format": "pt",
                "path": "{output_dir}/best.pt",
            }
        ],
    }
    assert payload["data"]["templates"][0]["execution_defaults"] == {
        "nproc_per_node": 1,
    }
    assert payload["data"]["queues"] == [
        {
            "queue_name": "queue_train_gpu",
            "agent_count": 1,
            "has_online_agents": True,
            "agents": [{"name": "agent-1", "status": "online"}],
            "last_seen": "2026-06-06T08:00:00Z",
        }
    ]


@pytest.mark.anyio
async def test_training_create_meta_degrades_when_queue_probe_fails():
    app = build_test_client()

    from app.api.routers import get_clearml_adapter

    async def override_clearml_adapter():
        return FailingClearMLAdapter()

    app.dependency_overrides[get_clearml_adapter] = override_clearml_adapter

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/mlops/training/create-meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["templates"][0]["name"] == "yolo-default"
    assert payload["data"]["queues"] == []
    assert payload["warnings"] == [
        "Queue metadata is temporarily unavailable. Template data is still returned."
    ]


@pytest.mark.anyio
async def test_create_training_uses_envelope_warnings_only():
    app = build_test_client()
    service = StubTrainingCommandService()

    from app.api.routers import get_training_command_service

    async def override_training_command_service():
        return service

    app.dependency_overrides[get_training_command_service] = (
        override_training_command_service
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/mlops/training",
            json={
                "task_name": "train-created",
                "template_name": "yolo-default",
                "params": {"epochs": 10},
                "execution_params": {"nproc_per_node": 2},
                "queue_name": "queue_train_gpu",
                "custom_data": {},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["warnings"] == [
        "Queue 'queue_train_gpu' has no online agents. The task will remain queued until an agent comes online."
    ]
    assert service.last_payload["execution_params"] == {"nproc_per_node": 2}
    assert "warnings" not in payload["data"]
    assert payload["data"]["task"]["task_name"] == "train-created"
    assert payload["data"]["submission"]["clearml_task_id"] == "clearml-02"


@pytest.mark.anyio
async def test_create_conversion_uses_envelope_warnings_only():
    app = build_test_client()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/mlops/conversion/onnx",
            json={
                "parent_task_id": 1,
                "task_name": "train-demo-export-onnx",
                "params": {"opset": 17},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["warnings"] == []
    assert "warnings" not in payload["data"]
    assert payload["data"]["task"]["task_type"] == "export_onnx"
    assert payload["data"]["submission"]["clearml_task_id"] == "clearml-03"
