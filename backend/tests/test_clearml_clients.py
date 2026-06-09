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
        "entrypoint": "generic_clearml_wrapper.py",
        "queue": "train_convnext",
        "parameters": {
            "batch": 64,
            "data": "/data/train",
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
        "payload": requests[0][2]["json"],
    }
    assert requests[0][0] == "POST"
    assert requests[0][1] == "/tasks.create"
    assert requests[1][0] == "POST"
    assert requests[1][1] == "/tasks.enqueue"

    request_payload = requests[0][2]["json"]
    assert request_payload["name"] == "convnext-train-a"
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
    assert requests[1][2]["json"] == {
        "task": "task-123",
        "queue": "queue-123",
    }
