from __future__ import annotations

from typing import Protocol

from adapter_context import AdapterContext


class TaskAdapter(Protocol):
    name: str

    def run(self, ctx: AdapterContext) -> int:
        ...
