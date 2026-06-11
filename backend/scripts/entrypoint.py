#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from adapter_context import AdapterContext
from adapters.generic import GenericAdapter
from adapters.onnx_export import OnnxExportAdapter
from adapters.training import TrainingAdapter
import clearml_runner


ADAPTERS = {
    GenericAdapter.name: GenericAdapter,
    OnnxExportAdapter.name: OnnxExportAdapter,
    TrainingAdapter.name: TrainingAdapter,
}


def resolve_adapter_name(runtime: dict[str, object]) -> str:
    adapter_name = runtime.get("adapter")
    if isinstance(adapter_name, str) and adapter_name:
        if adapter_name not in ADAPTERS:
            raise RuntimeError(f"Unsupported runtime.adapter '{adapter_name}'")
        return adapter_name
    raise RuntimeError("Runtime.adapter must be set")


def build_context(task) -> AdapterContext:
    raw_parameters = clearml_runner.task_parameters(task)
    sections = clearml_runner.extract_parameters(raw_parameters)
    runtime = clearml_runner.normalize_mapping(sections.get("Runtime"))
    args = clearml_runner.normalize_mapping(sections.get("Args"))
    command = clearml_runner.build_command(runtime, args)
    env = clearml_runner.build_runtime_env(runtime)
    working_dir = runtime.get("working_dir")
    if not isinstance(working_dir, str) or not working_dir:
        working_dir = None
    elif not Path(working_dir).exists():
        print(
            f"[generic-wrapper] working directory does not exist yet: {working_dir}",
            file=sys.stderr,
        )
    return AdapterContext(
        task_id=clearml_runner.task_id_for(task),
        task=task,
        args=args,
        runtime=runtime,
        working_dir=working_dir,
        env=env,
        command=command,
        adapter_name=resolve_adapter_name(runtime),
        trace=lambda message: clearml_runner.trace(task, message),
    )


def load_adapter(adapter_name: str):
    adapter_cls = ADAPTERS.get(adapter_name)
    if adapter_cls is None:
        raise RuntimeError(f"Unsupported runtime.adapter '{adapter_name}'")
    return adapter_cls()


def main() -> int:
    task = clearml_runner.current_task()
    if task is None:
        raise RuntimeError("No active ClearML task context was found")
    ctx = build_context(task)
    adapter = load_adapter(ctx.adapter_name)
    return adapter.run(ctx)


if __name__ == "__main__":
    raise SystemExit(main())
