from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_clearml_wrapper_source() -> str:
    wrapper_path = Path(__file__).resolve().parents[3] / "scripts" / "generic_clearml_wrapper.py"
    if not wrapper_path.exists():
        raise FileNotFoundError(
            f"ClearML wrapper source not found: {wrapper_path}"
        )
    return wrapper_path.read_text(encoding="utf-8")
