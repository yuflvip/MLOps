from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=1)
def load_clearml_wrapper_source() -> str:
    scripts_root = Path(__file__).resolve().parents[3] / "scripts"
    bundled_files = {
        "entrypoint.py": _read_required_file(scripts_root / "entrypoint.py"),
        "clearml_runner.py": _read_required_file(scripts_root / "clearml_runner.py"),
        "adapter_context.py": _read_required_file(scripts_root / "adapter_context.py"),
        "adapters/__init__.py": _read_required_file(
            scripts_root / "adapters" / "__init__.py"
        ),
        "adapters/base.py": _read_required_file(scripts_root / "adapters" / "base.py"),
        "adapters/generic.py": _read_required_file(
            scripts_root / "adapters" / "generic.py"
        ),
        "adapters/training.py": _read_required_file(
            scripts_root / "adapters" / "training.py"
        ),
        "adapters/onnx_export.py": _read_required_file(
            scripts_root / "adapters" / "onnx_export.py"
        ),
    }
    return _build_bootstrap_source(bundled_files)


def _read_required_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"ClearML wrapper source not found: {path}")
    return path.read_text(encoding="utf-8")


def _build_bootstrap_source(bundled_files: dict[str, str]) -> str:
    files_json = json.dumps(bundled_files, ensure_ascii=True, sort_keys=True)
    return f"""#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile


BUNDLED_FILES = json.loads({files_json!r})


def _materialize_bundle() -> Path:
    bundle_root = Path(tempfile.gettempdir()) / "clearml_wrapper_bundle"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=True)

    for relative_path, content in BUNDLED_FILES.items():
        file_path = bundle_root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    return bundle_root


def main() -> int:
    bundle_root = _materialize_bundle()
    if str(bundle_root) not in sys.path:
        sys.path.insert(0, str(bundle_root))
    from entrypoint import main as entrypoint_main

    return int(entrypoint_main())


if __name__ == "__main__":
    raise SystemExit(main())
"""
