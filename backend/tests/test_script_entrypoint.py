import importlib.util
import sys
import types
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_entrypoint_resolves_training_adapter():
    module = _load_module("entrypoint", SCRIPTS_DIR / "entrypoint.py")

    assert module.resolve_adapter_name({"adapter": "training"}) == "training"
    assert module.resolve_adapter_name({"adapter": "onnx_export"}) == "onnx_export"


def test_entrypoint_requires_runtime_adapter():
    module = _load_module("entrypoint", SCRIPTS_DIR / "entrypoint.py")

    try:
        module.resolve_adapter_name({})
    except RuntimeError as exc:
        assert str(exc) == "Runtime.adapter must be set"
    else:
        raise AssertionError("Expected RuntimeError")


def test_entrypoint_rejects_unsupported_runtime_adapter():
    module = _load_module("entrypoint", SCRIPTS_DIR / "entrypoint.py")

    try:
        module.resolve_adapter_name({"adapter": "bad"})
    except RuntimeError as exc:
        assert "Unsupported runtime.adapter 'bad'" == str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_training_adapter_prefers_current_task(monkeypatch):
    adapter_module = _load_module(
        "training_adapter",
        SCRIPTS_DIR / "adapters" / "training.py",
    )
    generic_module = _load_module(
        "generic_adapter",
        SCRIPTS_DIR / "adapters" / "generic.py",
    )
    context_module = _load_module("adapter_context", SCRIPTS_DIR / "adapter_context.py")

    captured = {}

    class _FakeTask:
        def __init__(self):
            self.status = "in_progress"

        def upload_artifact(self, *args, **kwargs):
            return None

        def flush(self, **kwargs):
            return True

    class _FakeClearMLTask:
        @staticmethod
        def current_task():
            return _FakeTask()

        @staticmethod
        def get_task(task_id):
            captured["task_id"] = task_id
            return _FakeTask()

    fake_clearml = types.SimpleNamespace(Task=_FakeClearMLTask)
    monkeypatch.setitem(sys.modules, "clearml", fake_clearml)
    monkeypatch.setattr(generic_module.clearml_runner, "run_subprocess", lambda *args, **kwargs: 0)
    monkeypatch.setattr(
        generic_module.clearml_runner,
        "upload_configured_artifacts",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(generic_module.clearml_runner, "trace", lambda *args, **kwargs: None)
    monkeypatch.setattr(generic_module.clearml_runner, "set_trace_path", lambda *args, **kwargs: None)

    ctx = context_module.AdapterContext(
        task_id="task-123",
        task=_FakeTask(),
        args={},
        runtime={},
        working_dir=None,
        env={},
        command=["python", "train.py"],
        adapter_name="training",
        trace=lambda message: None,
    )

    adapter = adapter_module.TrainingAdapter()
    result = adapter.run(ctx)

    assert result == 0
    assert "task_id" not in captured


def test_training_adapter_falls_back_to_get_task_by_existing_task_id(monkeypatch):
    adapter_module = _load_module(
        "training_adapter_get_task",
        SCRIPTS_DIR / "adapters" / "training.py",
    )
    generic_module = _load_module(
        "generic_adapter_get_task",
        SCRIPTS_DIR / "adapters" / "generic.py",
    )
    context_module = _load_module("adapter_context_get_task", SCRIPTS_DIR / "adapter_context.py")

    captured = {}

    class _FakeTask:
        def __init__(self):
            self.status = "in_progress"

        def upload_artifact(self, *args, **kwargs):
            return None

        def flush(self, **kwargs):
            return True

    class _FakeClearMLTask:
        @staticmethod
        def current_task():
            return None

        @staticmethod
        def get_task(task_id):
            captured["task_id"] = task_id
            return _FakeTask()

    fake_clearml = types.SimpleNamespace(Task=_FakeClearMLTask)
    monkeypatch.setitem(sys.modules, "clearml", fake_clearml)
    monkeypatch.setattr(generic_module.clearml_runner, "run_subprocess", lambda *args, **kwargs: 0)
    monkeypatch.setattr(
        generic_module.clearml_runner,
        "upload_configured_artifacts",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(generic_module.clearml_runner, "trace", lambda *args, **kwargs: None)
    monkeypatch.setattr(generic_module.clearml_runner, "set_trace_path", lambda *args, **kwargs: None)

    ctx = context_module.AdapterContext(
        task_id="task-123",
        task=_FakeTask(),
        args={},
        runtime={},
        working_dir=None,
        env={},
        command=["python", "train.py"],
        adapter_name="training",
        trace=lambda message: None,
    )

    adapter = adapter_module.TrainingAdapter()
    result = adapter.run(ctx)

    assert result == 0
    assert captured["task_id"] == "task-123"


def test_training_adapter_reports_scalars_and_registers_models(monkeypatch, tmp_path):
    adapter_module = _load_module(
        "training_adapter_reporting",
        SCRIPTS_DIR / "adapters" / "training.py",
    )
    generic_module = _load_module(
        "generic_adapter_reporting",
        SCRIPTS_DIR / "adapters" / "generic.py",
    )
    context_module = _load_module("adapter_context_reporting", SCRIPTS_DIR / "adapter_context.py")

    (tmp_path / "results.csv").write_text(
        "\n".join(
            [
                "epoch,train_loss,val_loss,train_acc_top1,val_acc_top1,lr,epoch_time_sec",
                "1,1.25,1.10,0.80,0.82,0.0001,12.5",
                "2,0.95,0.88,0.86,0.89,0.00005,11.9",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "best.pth").write_text("best", encoding="utf-8")
    (tmp_path / "last.pth").write_text("last", encoding="utf-8")

    reported = []
    registered = []

    class _FakeTask:
        def __init__(self):
            self.status = "completed"
            self.flushed = 0

        def upload_artifact(self, *args, **kwargs):
            return None

        def flush(self, **kwargs):
            self.flushed += 1
            return True

        def update_output_model(self, **kwargs):
            registered.append(kwargs)
            return f"model-{len(registered)}"

    fake_task = _FakeTask()
    
    class _FakeLoggerInstance:
        def report_scalar(self, title, series, value, iteration):
            reported.append(
                {
                    "title": title,
                    "series": series,
                    "value": value,
                    "iteration": iteration,
                }
            )

    fake_logger = _FakeLoggerInstance()

    def _get_logger():
        return fake_logger

    fake_task.get_logger = _get_logger

    class _FakeClearMLTask:
        @staticmethod
        def current_task():
            return fake_task

        @staticmethod
        def get_task(task_id):
            return fake_task

    fake_clearml = types.SimpleNamespace(Task=_FakeClearMLTask)
    monkeypatch.setitem(sys.modules, "clearml", fake_clearml)
    monkeypatch.setattr(generic_module.clearml_runner, "run_subprocess", lambda *args, **kwargs: 0)
    monkeypatch.setattr(
        generic_module.clearml_runner,
        "upload_configured_artifacts",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(generic_module.clearml_runner, "trace", lambda *args, **kwargs: None)
    monkeypatch.setattr(generic_module.clearml_runner, "set_trace_path", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        adapter_module.clearml_runner,
        "build_artifact_context",
        lambda **kwargs: {"output_dir": str(tmp_path)},
    )
    monkeypatch.setattr(adapter_module.clearml_runner, "trace", lambda *args, **kwargs: None)

    ctx = context_module.AdapterContext(
        task_id="task-456",
        task=fake_task,
        args={},
        runtime={},
        working_dir=str(tmp_path),
        env={},
        command=["python", "train.py"],
        adapter_name="training",
        trace=lambda message: None,
    )

    adapter = adapter_module.TrainingAdapter()
    result = adapter.run(ctx)

    assert result == 0
    assert {"title": "loss", "series": "train", "value": 1.25, "iteration": 1} in reported
    assert {"title": "acc_top1", "series": "val", "value": 0.89, "iteration": 2} in reported
    assert {"title": "lr", "series": "train", "value": 0.0001, "iteration": 1} in reported
    assert len(registered) == 2
    assert registered[0]["model_path"].endswith("best.pth")
    assert registered[1]["model_path"].endswith("last.pth")
    assert fake_task.flushed >= 1


def test_training_adapter_skips_scalars_when_logger_unavailable(monkeypatch, tmp_path):
    adapter_module = _load_module(
        "training_adapter_no_logger",
        SCRIPTS_DIR / "adapters" / "training.py",
    )
    generic_module = _load_module(
        "generic_adapter_no_logger",
        SCRIPTS_DIR / "adapters" / "generic.py",
    )
    context_module = _load_module("adapter_context_no_logger", SCRIPTS_DIR / "adapter_context.py")

    (tmp_path / "results.csv").write_text(
        "epoch,train_loss\n1,1.25\n",
        encoding="utf-8",
    )

    class _FakeTask:
        def __init__(self):
            self.status = "completed"

        def upload_artifact(self, *args, **kwargs):
            return None

        def flush(self, **kwargs):
            return True

        def get_logger(self):
            return None

        def update_output_model(self, **kwargs):
            return "model-1"

    fake_task = _FakeTask()

    class _FakeClearMLTask:
        @staticmethod
        def current_task():
            return fake_task

        @staticmethod
        def get_task(task_id):
            return fake_task

    fake_clearml = types.SimpleNamespace(Task=_FakeClearMLTask)
    monkeypatch.setitem(sys.modules, "clearml", fake_clearml)
    monkeypatch.setattr(generic_module.clearml_runner, "run_subprocess", lambda *args, **kwargs: 0)
    monkeypatch.setattr(
        generic_module.clearml_runner,
        "upload_configured_artifacts",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(generic_module.clearml_runner, "trace", lambda *args, **kwargs: None)
    monkeypatch.setattr(generic_module.clearml_runner, "set_trace_path", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        adapter_module.clearml_runner,
        "build_artifact_context",
        lambda **kwargs: {"output_dir": str(tmp_path)},
    )
    monkeypatch.setattr(adapter_module.clearml_runner, "trace", lambda *args, **kwargs: None)

    ctx = context_module.AdapterContext(
        task_id="task-789",
        task=fake_task,
        args={},
        runtime={},
        working_dir=str(tmp_path),
        env={},
        command=["python", "train.py"],
        adapter_name="training",
        trace=lambda message: None,
    )

    adapter = adapter_module.TrainingAdapter()
    result = adapter.run(ctx)

    assert result == 0


def test_onnx_export_adapter_does_not_call_task_init(monkeypatch):
    adapter_module = _load_module(
        "onnx_export_adapter",
        SCRIPTS_DIR / "adapters" / "onnx_export.py",
    )
    generic_module = _load_module(
        "generic_adapter_for_onnx",
        SCRIPTS_DIR / "adapters" / "generic.py",
    )
    context_module = _load_module("adapter_context_for_onnx", SCRIPTS_DIR / "adapter_context.py")

    called = {"init": 0}

    class _FakeTask:
        def __init__(self):
            self.status = "queued"

        def upload_artifact(self, *args, **kwargs):
            return None

        def flush(self, **kwargs):
            return True

    class _FakeClearMLTask:
        @staticmethod
        def init(task_id):
            called["init"] += 1
            return _FakeTask()

    fake_clearml = types.SimpleNamespace(Task=_FakeClearMLTask)
    monkeypatch.setitem(sys.modules, "clearml", fake_clearml)
    monkeypatch.setattr(generic_module.clearml_runner, "run_subprocess", lambda *args, **kwargs: 0)
    monkeypatch.setattr(
        generic_module.clearml_runner,
        "upload_configured_artifacts",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(generic_module.clearml_runner, "trace", lambda *args, **kwargs: None)
    monkeypatch.setattr(generic_module.clearml_runner, "set_trace_path", lambda *args, **kwargs: None)
    monkeypatch.setattr(adapter_module.clearml_runner, "trace", lambda *args, **kwargs: None)

    ctx = context_module.AdapterContext(
        task_id="task-onnx-123",
        task=_FakeTask(),
        args={"opset": 17},
        runtime={"adapter": "onnx_export"},
        working_dir=None,
        env={},
        command=["python", "export.py", "--opset", "17"],
        adapter_name="onnx_export",
        trace=lambda message: None,
    )

    adapter = adapter_module.OnnxExportAdapter()
    result = adapter.run(ctx)

    assert result == 0
    assert called["init"] == 0
