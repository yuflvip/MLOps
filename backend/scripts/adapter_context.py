from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class AdapterContext:
    task_id: str
    task: Any
    args: dict[str, Any]
    runtime: dict[str, Any]
    working_dir: str | None
    env: dict[str, str]
    command: list[str]
    adapter_name: str
    trace: Callable[[str], None]
    task_type: str | None = None
