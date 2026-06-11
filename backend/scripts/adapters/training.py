from __future__ import annotations

import csv
from pathlib import Path

from adapter_context import AdapterContext
from adapters.generic import GenericAdapter
import clearml_runner


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> int | None:
    number = _safe_float(value)
    if number is None:
        return None
    return int(number)


def _resolve_output_dir(ctx: AdapterContext) -> Path | None:
    context = clearml_runner.build_artifact_context(
        args=ctx.args,
        runtime=ctx.runtime,
        working_dir=ctx.working_dir,
    )
    output_dir = context.get("output_dir")
    if isinstance(output_dir, str) and output_dir:
        return Path(output_dir)
    return None


def _report_results_csv(task, output_dir: Path) -> int:
    results_path = output_dir / "results.csv"
    if not results_path.exists():
        clearml_runner.trace(task, f"[training-adapter] results.csv not found: {results_path}")
        return 0

    logger = task.get_logger() if task is not None and hasattr(task, "get_logger") else None
    if logger is None:
        clearml_runner.trace(task, "[training-adapter] logger unavailable, skip scalar reporting")
        return 0

    reported = 0
    with results_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            iteration = _safe_int(row.get("epoch"))
            if iteration is None:
                continue
            for key, raw_value in row.items():
                if key == "epoch":
                    continue
                value = _safe_float(raw_value)
                if value is None:
                    continue
                series = "train"
                title = key
                if "_" in key:
                    maybe_series, remainder = key.split("_", 1)
                    if maybe_series in {"train", "val", "test"} and remainder:
                        series = maybe_series
                        title = remainder
                logger.report_scalar(title=title, series=series, value=value, iteration=iteration)
                reported += 1
    return reported


def _register_model(task, output_dir: Path) -> list[str]:
    registered: list[str] = []
    for filename, model_name in (("best.pth", "best"), ("last.pth", "last")):
        model_path = output_dir / filename
        if not model_path.exists():
            continue
        task.update_output_model(
            model_path=str(model_path),
            name=model_name,
            model_name=model_name,
            auto_delete_file=False,
        )
        registered.append(filename)
    return registered


class TrainingAdapter(GenericAdapter):
    name = "training"

    def run(self, ctx: AdapterContext) -> int:
        from clearml import Task

        task = Task.current_task()
        if task is None:
            task = Task.get_task(task_id=ctx.task_id)
        ctx.task = task
        returncode = super().run(ctx)
        if returncode != 0:
            return returncode

        output_dir = _resolve_output_dir(ctx)
        if output_dir is None:
            clearml_runner.trace(task, "[training-adapter] output_dir not resolved, skip metrics/model sync")
            return returncode

        reported = _report_results_csv(task, output_dir)
        clearml_runner.trace(task, f"[training-adapter] reported_scalars={reported}")

        registered = _register_model(task, output_dir)
        clearml_runner.trace(
            task,
            "[training-adapter] registered_models=" + ",".join(registered) if registered else "[training-adapter] registered_models=0",
        )
        task.flush(wait_for_uploads=True)
        return returncode
