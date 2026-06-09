from app.infrastructure.clearml.clients import HttpClearMLClient


def test_http_clearml_client_builds_tasks_create_request():
    client = HttpClearMLClient(
        api_base_url="http://clearml.example",
        access_key="access",
        secret_key="secret",
    )
    client._resolve_queue_id = lambda queue_name: "queue-123"  # type: ignore[method-assign]

    requests = []

    def fake_request(method, path, **kwargs):
        requests.append((method, path, kwargs))
        if path == "/projects.get_all":
            return {
                "data": {
                    "projects": [
                        {
                            "id": "project-123",
                            "name": "classify_vehicle_10class",
                        }
                    ]
                }
            }
        if path == "/tasks.create":
            return {
                "data": {
                    "id": "task-123",
                }
            }
        if path == "/tasks.enqueue":
            return {
                "data": {
                    "queued": 1,
                }
            }
        raise AssertionError(f"Unexpected request path: {path}")

    client._request = fake_request  # type: ignore[attr-defined]

    payload = {
        "name": "convnext-train-a",
        "project": "classify_vehicle_10class",
        "entrypoint": "generic_clearml_wrapper.py",
        "queue": "train_convnext",
        "parameters": {
            "batch": 64,
            "data": "/data/train",
            "project": "classify_vehicle_10class",
            "epochs": 1,
        },
        "runtime": {
            "launcher": "torchrun",
            "script_path": "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls/tools/train.py",
            "working_dir": "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls",
            "execution_params": {
                "cuda_visible_devices": "2",
                "nproc_per_node": 1,
            },
            "env": {
                "CUDA_VISIBLE_DEVICES": "2",
                "NCCL_IB_DISABLE": 1,
                "NCCL_P2P_DISABLE": 0,
            },
        },
        "execution_defaults": {
            "nproc_per_node": 1,
        },
    }

    result = client.create_task(payload)

    assert result == {
        "id": "task-123",
        "status": "queued",
        "payload": requests[1][2]["json"],
    }
    assert requests[0][0] == "POST"
    assert requests[0][1] == "/projects.get_all"
    assert requests[1][0] == "POST"
    assert requests[1][1] == "/tasks.create"
    assert requests[2][0] == "POST"
    assert requests[2][1] == "/tasks.enqueue"

    request_payload = requests[1][2]["json"]
    assert request_payload["name"] == "convnext-train-a"
    assert request_payload["project"] == "project-123"
    assert request_payload["type"] == "training"
    assert request_payload["execution"] == {"queue": "queue-123"}
    assert request_payload["script"]["entry_point"] == "generic_clearml_wrapper.py"
    assert request_payload["script"]["working_dir"] == "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls"
    assert request_payload["script"]["diff"].startswith("#!/usr/bin/env python3")
    assert request_payload["hyperparams"]["Args"]["batch"] == {
        "name": "batch",
        "section": "Args",
        "type": "int",
        "value": "64",
    }
    assert request_payload["hyperparams"]["Runtime"]["execution_params"] == {
        "name": "execution_params",
        "section": "Runtime",
        "type": "str",
        "value": '{"cuda_visible_devices": "2", "nproc_per_node": 1}',
    }
    assert requests[2][2]["json"] == {
        "task": "task-123",
        "queue": "queue-123",
    }


def test_http_clearml_client_uses_project_from_parameters_when_missing_top_level_project():
    client = HttpClearMLClient(
        api_base_url="http://clearml.example",
        access_key="access",
        secret_key="secret",
    )
    client._resolve_queue_id = lambda queue_name: "queue-123"  # type: ignore[method-assign]

    requests = []

    def fake_request(method, path, **kwargs):
        requests.append((method, path, kwargs))
        if path == "/projects.get_all":
            return {"data": {"projects": []}}
        if path == "/projects.create":
            return {"data": {"id": "project-789"}}
        if path == "/tasks.create":
            return {"data": {"id": "task-123"}}
        if path == "/tasks.enqueue":
            return {"data": {"queued": 1}}
        raise AssertionError(f"Unexpected request path: {path}")

    client._request = fake_request  # type: ignore[attr-defined]

    client.create_task(
        {
            "name": "convnext-train-a",
            "entrypoint": "generic_clearml_wrapper.py",
            "queue": "train_convnext",
            "parameters": {
                "project": "classify_vehicle_10class",
            },
            "runtime": {
                "launcher": "torchrun",
                "script_path": "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls/tools/train.py",
                "working_dir": "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls",
            },
        }
    )

    assert requests[0][1] == "/projects.get_all"
    assert requests[1][1] == "/projects.create"
    assert requests[1][2]["json"] == {"name": "classify_vehicle_10class"}
    request_payload = requests[2][2]["json"]
    assert request_payload["project"] == "project-789"


def test_http_clearml_client_gets_tasks_by_ids():
    client = HttpClearMLClient(
        api_base_url="http://clearml.example",
        access_key="access",
        secret_key="secret",
    )

    requests = []

    def fake_request(method, path, **kwargs):
        requests.append((method, path, kwargs))
        if path == "/tasks.get_all":
            return {
                "data": {
                    "tasks": [
                        {"id": "task-1", "status": "in_progress"},
                        {"id": "task-2", "status": "completed"},
                    ]
                }
            }
        raise AssertionError(f"Unexpected request path: {path}")

    client._request = fake_request  # type: ignore[attr-defined]

    payload = client.get_tasks(["task-1", "task-2"])

    assert payload == [
        {"id": "task-1", "status": "in_progress"},
        {"id": "task-2", "status": "completed"},
    ]
    assert requests == [
        (
            "POST",
            "/tasks.get_all",
            {
                "json": {
                    "id": ["task-1", "task-2"],
                    "only_fields": ["id", "status", "status_message", "status_reason"],
                }
            },
        )
    ]
