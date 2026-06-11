#!/usr/bin/env python3
"""Compatibility entrypoint for the new runner + adapters layout."""

from __future__ import annotations

import sys
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from clearml_runner import (  # noqa: E402
    TRACE_PATH,
    build_artifact_context,
    build_command,
    build_runtime_env,
    build_script_args,
    coerce_cli_value as _coerce_cli_value,
    current_task as _current_task,
    discover_output_dir,
    extract_parameters as _extract_parameters,
    maybe_json_load as _maybe_json_load,
    normalize_mapping as _normalize_mapping,
    resolve_artifact_paths as _resolve_artifact_paths,
    SafeFormatDict as _SafeFormatDict,
    task_id_for as _task_id,
    trace as _trace,
    trace_path as _trace_path,
    upload_configured_artifacts,
)
from entrypoint import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
