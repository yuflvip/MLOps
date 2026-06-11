from __future__ import annotations

import json

from adapter_context import AdapterContext
import clearml_runner


class GenericAdapter:
    name = "generic"

    def run(self, ctx: AdapterContext) -> int:
        clearml_runner.trace(
            ctx.task,
            "[generic-wrapper] runtime: "
            + json.dumps(ctx.runtime, ensure_ascii=True, sort_keys=True),
        )
        clearml_runner.trace(
            ctx.task,
            "[generic-wrapper] command: " + " ".join(ctx.command),
        )
        if ctx.working_dir:
            clearml_runner.trace(ctx.task, "[generic-wrapper] cwd: " + ctx.working_dir)

        clearml_runner.set_trace_path(ctx.task, ctx.working_dir)
        clearml_runner.trace(
            ctx.task,
            f"[generic-wrapper] task_id={ctx.task_id} status={getattr(ctx.task, 'status', None)}",
        )
        clearml_runner.trace(
            ctx.task,
            f"[generic-wrapper] before subprocess status={getattr(ctx.task, 'status', None)}",
        )
        returncode = clearml_runner.run_subprocess(
            ctx.command,
            cwd=ctx.working_dir,
            env=ctx.env,
        )
        clearml_runner.trace(
            ctx.task,
            f"[generic-wrapper] after subprocess returncode={returncode} status={getattr(ctx.task, 'status', None)}",
        )
        if returncode == 0:
            artifact_context = clearml_runner.build_artifact_context(
                args=ctx.args,
                runtime=ctx.runtime,
                working_dir=ctx.working_dir,
            )
            clearml_runner.trace(
                ctx.task,
                f"[generic-wrapper] artifact context keys={sorted(artifact_context.keys())}",
            )
            uploaded = clearml_runner.upload_configured_artifacts(
                task=ctx.task,
                runtime=ctx.runtime,
                context=artifact_context,
            )
            clearml_runner.trace(
                ctx.task,
                f"[generic-wrapper] uploaded_count={len(uploaded)} status={getattr(ctx.task, 'status', None)}",
            )
            if uploaded:
                ctx.task.flush(wait_for_uploads=True)
                clearml_runner.trace(
                    ctx.task,
                    "[generic-wrapper] uploaded artifacts: " + ", ".join(uploaded),
                )
        clearml_runner.trace(
            ctx.task,
            f"[generic-wrapper] exiting status={getattr(ctx.task, 'status', None)} returncode={returncode}",
        )
        return returncode
