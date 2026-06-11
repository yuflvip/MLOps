#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from glob import glob
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


TRACE_PATH: Path | None = None


def maybe_json_load(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def normalize_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    loaded = maybe_json_load(value)
    if isinstance(loaded, dict):
        return dict(loaded)
    return {}


def extract_parameters(raw_parameters: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(raw_parameters, dict):
        return {"Args": {}, "Runtime": {}}

    if "Args" in raw_parameters or "Runtime" in raw_parameters:
        args = normalize_mapping(raw_parameters.get("Args"))
        runtime = normalize_mapping(raw_parameters.get("Runtime"))
        return {"Args": args, "Runtime": runtime}

    args: Dict[str, Any] = {}
    runtime: Dict[str, Any] = {}
    for key, value in raw_parameters.items():
        if not isinstance(key, str):
            continue
        if key.startswith("Args/"):
            args[key.split("/", 1)[1]] = value
        elif key.startswith("Runtime/"):
            runtime[key.split("/", 1)[1]] = value
    return {"Args": args, "Runtime": runtime}


def coerce_cli_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    return str(value)


def build_script_args(args: Dict[str, Any]) -> list[str]:
    cli_args: list[str] = []
    for key in sorted(args):
        value = args[key]
        if value is None:
            continue
        cli_args.append(f"--{key}")
        cli_args.append(coerce_cli_value(value))
    return cli_args


def build_runtime_env(runtime: Dict[str, Any]) -> Dict[str, str]:
    env = os.environ.copy()
    runtime_env = normalize_mapping(runtime.get("env"))
    for key, value in runtime_env.items():
        env[str(key)] = coerce_cli_value(value)

    execution_params = normalize_mapping(runtime.get("execution_params"))
    cuda_visible_devices = execution_params.get("cuda_visible_devices")
    if cuda_visible_devices is not None:
        env["CUDA_VISIBLE_DEVICES"] = coerce_cli_value(cuda_visible_devices)

    return env


def build_command(runtime: Dict[str, Any], args: Dict[str, Any]) -> list[str]:
    launcher = str(runtime.get("launcher") or "python").lower()
    script_path = runtime.get("script_path")
    if not isinstance(script_path, str) or not script_path:
        raise RuntimeError("Runtime.script_path must be set")

    script_args = build_script_args(args)
    execution_params = normalize_mapping(runtime.get("execution_params"))

    if launcher == "torchrun":
        nproc = execution_params.get("nproc_per_node")
        if nproc is None:
            nproc = normalize_mapping(runtime.get("launcher_args")).get(
                "nproc_per_node", 1
            )
        return [
            sys.executable,
            "-m",
            "torch.distributed.run",
            "--nproc_per_node",
            str(nproc),
            script_path,
            *script_args,
        ]

    if launcher == "shell":
        command = runtime.get("command")
        if not isinstance(command, str) or not command:
            raise RuntimeError("Runtime.command must be set for shell launcher")
        return ["/bin/bash", "-lc", command]

    return [sys.executable, script_path, *script_args]


def build_artifact_context(
    args: Dict[str, Any], runtime: Dict[str, Any], working_dir: str | None
) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    context.update(args)
    context.update(runtime)
    context["args"] = dict(args)
    context["runtime"] = dict(runtime)
    if working_dir:
        context["working_dir"] = working_dir
        output_dir = discover_output_dir(
            working_dir=working_dir,
            project=str(args.get("project")) if args.get("project") is not None else None,
            name=str(args.get("name")) if args.get("name") is not None else None,
        )
        if output_dir:
            context["output_dir"] = output_dir
    return context


def discover_output_dir(
    working_dir: str,
    project: str | None = None,
    name: str | None = None,
) -> str | None:
    runs_root = Path(working_dir) / "runs"
    if not runs_root.exists():
        return None

    candidates: list[tuple[float, Path, Dict[str, Any]]] = []
    for run_config_path in runs_root.rglob("run_config.json"):
        try:
            payload = json.loads(run_config_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        try:
            mtime = run_config_path.stat().st_mtime
        except OSError:
            continue
        candidates.append((mtime, run_config_path, payload))

    if not candidates:
        return None

    def matches(payload: Dict[str, Any], expect_name: bool) -> bool:
        task_config = payload.get("config", {}).get("task", {})
        if project and task_config.get("project") not in {None, project}:
            return False
        if expect_name and name and task_config.get("name") not in {None, name, f"{name}_final"}:
            return False
        return True

    for expect_name in (True, False):
        filtered = [item for item in candidates if matches(item[2], expect_name)]
        if filtered:
            filtered.sort(key=lambda item: item[0], reverse=True)
            payload = filtered[0][2]
            task_config = payload.get("config", {}).get("task", {})
            output_dir = task_config.get("output")
            if isinstance(output_dir, str) and output_dir:
                return output_dir
            return str(filtered[0][1].parent)

    candidates.sort(key=lambda item: item[0], reverse=True)
    payload = candidates[0][2]
    task_config = payload.get("config", {}).get("task", {})
    output_dir = task_config.get("output")
    if isinstance(output_dir, str) and output_dir:
        return output_dir
    return str(candidates[0][1].parent)


def upload_configured_artifacts(
    task: Any,
    runtime: Dict[str, Any],
    context: Dict[str, Any],
) -> list[str]:
    artifacts = maybe_json_load(runtime.get("artifacts"))
    if not isinstance(artifacts, list):
        return []

    uploaded: list[str] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        name = artifact.get("name")
        path_template = artifact.get("path")
        if not isinstance(name, str) or not name:
            continue
        if not isinstance(path_template, str) or not path_template:
            continue

        artifact_path = path_template.format_map(SafeFormatDict(context))
        matched_paths = resolve_artifact_paths(artifact_path)
        if not matched_paths:
            print(
                f"[generic-wrapper] artifact not found, skip upload: {name} -> {artifact_path}",
                file=sys.stderr,
            )
            continue

        metadata = {}
        for key in ("role", "format"):
            if artifact.get(key) is not None:
                metadata[key] = artifact.get(key)
        if artifact.get("metadata") and isinstance(artifact.get("metadata"), dict):
            metadata.update(artifact["metadata"])

        for matched_path in matched_paths:
            task.upload_artifact(
                name=name,
                artifact_object=matched_path,
                metadata=metadata or None,
                wait_on_upload=True,
            )
            uploaded.append(name)
            break
    return uploaded


def resolve_artifact_paths(artifact_path: str) -> list[str]:
    if any(char in artifact_path for char in ("*", "?", "[")):
        return sorted(glob(artifact_path))
    path = Path(artifact_path)
    if path.exists():
        return [str(path)]
    return []


def current_task():
    from clearml import Task

    task_id = os.environ.get("CLEARML_TASK_ID") or os.environ.get("CLEARML_TASK")
    if task_id:
        task = Task.get_task(task_id=task_id)
        if task is not None:
            return task

    task = Task.current_task()
    if task is not None:
        if task_id_for(task) != "unknown":
            return task
        if task_id:
            task = Task.get_task(task_id=task_id)
            if task is not None:
                return task
        return task
    return None


def task_id_for(task: Any) -> str:
    for attr in ("id", "task_id"):
        value = getattr(task, attr, None)
        if isinstance(value, str) and value:
            return value
    for env_key in ("CLEARML_TASK_ID", "CLEARML_TASK"):
        value = os.environ.get(env_key)
        if isinstance(value, str) and value:
            return value
    return "unknown"


def task_parameters(task: Any) -> Dict[str, Any]:
    raw_parameters = {}
    if hasattr(task, "get_parameters_as_dict"):
        raw_parameters = task.get_parameters_as_dict(cast=False) or {}
    elif hasattr(task, "get_parameters"):
        raw_parameters = task.get_parameters(
            backwards_compatibility=False, cast=False
        ) or {}
    return raw_parameters


def set_trace_path(task: Any, working_dir: str | None) -> Path:
    global TRACE_PATH
    if working_dir:
        TRACE_PATH = Path(working_dir) / f".generic_clearml_wrapper_{task_id_for(task)}.log"
    else:
        TRACE_PATH = Path(tempfile.gettempdir()) / f"generic_clearml_wrapper_{task_id_for(task)}.log"
    return TRACE_PATH


def trace_path(task: Any) -> Path:
    if TRACE_PATH is not None:
        return TRACE_PATH
    return Path(tempfile.gettempdir()) / f"generic_clearml_wrapper_{task_id_for(task)}.log"


def trace(task: Any, message: str) -> None:
    line = message.rstrip("\n")
    print(line, flush=True)
    try:
        path = trace_path(task)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass


def run_subprocess(
    command: list[str],
    *,
    cwd: str | None,
    env: dict[str, str],
) -> int:
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    return int(completed.returncode)


class SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
