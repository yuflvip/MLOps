from __future__ import annotations

import clearml_runner
from adapter_context import AdapterContext
from adapters.generic import GenericAdapter


class OnnxExportAdapter(GenericAdapter):
    name = "onnx_export"

    def run(self, ctx: AdapterContext) -> int:
        clearml_runner.trace(
            ctx.task,
            f"[onnx-export] task_id={ctx.task_id} adapter={self.name}",
        )
        return super().run(ctx)
