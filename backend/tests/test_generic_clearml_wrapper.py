import json
import importlib.util
import sys
import types
from pathlib import Path


def _load_wrapper_module():
    wrapper_path = Path(__file__).resolve().parents[1] / "scripts" / "generic_clearml_wrapper.py"
    spec = importlib.util.spec_from_file_location(
        "generic_clearml_wrapper", wrapper_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_generic_wrapper_builds_torchrun_command_and_runtime_env():
    module = _load_wrapper_module()

    runtime = {
        "launcher": "torchrun",
        "script_path": "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls/tools/train.py",
        "working_dir": "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls",
        "env": {
            "NCCL_IB_DISABLE": 1,
            "NCCL_P2P_DISABLE": 0,
        },
        "execution_params": {
            "nproc_per_node": 2,
            "cuda_visible_devices": "1",
        },
    }
    args = {
        "batch": 64,
        "dynamic": False,
        "epochs": 1,
    }

    command = module.build_command(runtime, args)
    env = module.build_runtime_env(runtime)

    assert command == [
        module.sys.executable,
        "-m",
        "torch.distributed.run",
        "--nproc_per_node",
        "2",
        "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls/tools/train.py",
        "--batch",
        "64",
        "--dynamic",
        "false",
        "--epochs",
        "1",
    ]
    assert env["CUDA_VISIBLE_DEVICES"] == "1"
    assert env["NCCL_IB_DISABLE"] == "1"
    assert env["NCCL_P2P_DISABLE"] == "0"


def test_generic_wrapper_uploads_configured_artifacts_on_success(tmp_path):
    module = _load_wrapper_module()
    output_dir = tmp_path / "runs" / "classify" / "classify_vehicle_10class" / "exp_20260608_final"
    output_dir.mkdir(parents=True)
    best_pt = output_dir / "best.pt"
    results_csv = output_dir / "results.csv"
    run_config = output_dir / "run_config.json"
    best_pt.write_text("best", encoding="utf-8")
    results_csv.write_text("results", encoding="utf-8")
    run_config.write_text(
        """
{
  "config": {
    "task": {
      "project": "classify_vehicle_10class",
      "name": "exp_20260608_final",
      "output": "%s"
    }
  }
}
""".strip()
        % output_dir,
        encoding="utf-8",
    )

    runtime = {
        "launcher": "python",
        "script_path": "train.py",
        "working_dir": str(tmp_path),
        "artifacts": [
            {
                "name": "best_model",
                "path": "{output_dir}/best.pt",
                "role": "model_weight",
                "format": "pt",
            },
            {
                "name": "metrics",
                "path": "{output_dir}/results.csv",
                "role": "metrics",
                "format": "csv",
            },
        ],
    }
    task = _FakeTask()

    context = module.build_artifact_context(
        args={"project": "classify_vehicle_10class", "name": "exp_20260608_final"},
        runtime=runtime,
        working_dir=str(tmp_path),
    )
    uploaded = module.upload_configured_artifacts(
        task=task,
        runtime=runtime,
        context=context,
    )

    assert uploaded == ["best_model", "metrics"]
    assert task.uploaded == [
        {
            "name": "best_model",
            "artifact_object": str(best_pt),
            "metadata": {
                "format": "pt",
                "role": "model_weight",
            },
        },
        {
            "name": "metrics",
            "artifact_object": str(results_csv),
            "metadata": {
                "format": "csv",
                "role": "metrics",
            },
        },
    ]


def test_generic_wrapper_uploads_stringified_runtime_artifacts(tmp_path):
    module = _load_wrapper_module()
    output_dir = tmp_path / "runs" / "classify" / "classify_vehicle_10class" / "exp_20260608_final"
    output_dir.mkdir(parents=True)
    best_pt = output_dir / "best.pt"
    best_pt.write_text("best", encoding="utf-8")
    (output_dir / "run_config.json").write_text(
        """
{
  "config": {
    "task": {
      "project": "classify_vehicle_10class",
      "name": "exp_20260608_final",
      "output": "%s"
    }
  }
}
""".strip()
        % output_dir,
        encoding="utf-8",
    )

    runtime = {
        "launcher": "python",
        "script_path": "train.py",
        "working_dir": str(tmp_path),
        "artifacts": json.dumps(
            [
                {
                    "name": "best_model",
                    "path": "{output_dir}/best.pt",
                    "role": "model_weight",
                    "format": "pt",
                }
            ]
        ),
    }
    task = _FakeTask()

    context = module.build_artifact_context(
        args={"project": "classify_vehicle_10class", "name": "exp_20260608_final"},
        runtime=runtime,
        working_dir=str(tmp_path),
    )
    uploaded = module.upload_configured_artifacts(
        task=task,
        runtime=runtime,
        context=context,
    )

    assert uploaded == ["best_model"]
    assert task.uploaded == [
        {
            "name": "best_model",
            "artifact_object": str(best_pt),
            "metadata": {
                "format": "pt",
                "role": "model_weight",
            },
        }
    ]


def test_generic_wrapper_discovers_output_dir_from_run_config(tmp_path):
    module = _load_wrapper_module()
    output_dir = tmp_path / "runs" / "classify" / "classify_vehicle_10class" / "exp_20260608_final"
    output_dir.mkdir(parents=True)
    (output_dir / "run_config.json").write_text(
        """
{
  "config": {
    "task": {
      "project": "classify_vehicle_10class",
      "name": "exp_20260608_final",
      "output": "%s"
    }
  }
}
""".strip()
        % output_dir,
        encoding="utf-8",
    )

    discovered = module.discover_output_dir(
        working_dir=str(tmp_path),
        project="classify_vehicle_10class",
        name="exp_20260608_auto_artifact_v2",
    )

    assert discovered == str(output_dir)


def test_generic_wrapper_task_id_falls_back_to_clearml_env(monkeypatch):
    module = _load_wrapper_module()
    monkeypatch.setenv("CLEARML_TASK_ID", "task-123")

    class _Task:
        id = None
        task_id = None

    assert module._task_id(_Task()) == "task-123"


def test_generic_wrapper_current_task_prefers_clearml_task_id_env(monkeypatch):
    module = _load_wrapper_module()
    monkeypatch.setenv("CLEARML_TASK_ID", "task-123")

    class _FakeTask:
        @staticmethod
        def current_task():
            return None

        @staticmethod
        def get_task(task_id):
            return {"task_id": task_id}

    fake_clearml = types.SimpleNamespace(Task=_FakeTask)
    monkeypatch.setitem(sys.modules, "clearml", fake_clearml)

    try:
        assert module._current_task() == {"task_id": "task-123"}
    finally:
        monkeypatch.delitem(sys.modules, "clearml", raising=False)


class _FakeTask:
    def __init__(self):
        self.uploaded = []
        self.flushed = False

    def upload_artifact(self, name, artifact_object, metadata=None, **_kwargs):
        self.uploaded.append(
            {
                "name": name,
                "artifact_object": artifact_object,
                "metadata": metadata,
            }
        )

    def flush(self, wait_for_uploads=False):
        self.flushed = wait_for_uploads
        return True
