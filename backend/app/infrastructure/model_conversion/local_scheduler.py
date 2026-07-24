import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.infrastructure.config.settings import ModelConversionSettings
from app.infrastructure.db.models import ExpModel, ModelConversionModel


class LocalModelConversionScheduler:
    def __init__(
        self,
        *,
        session_factory,
        settings: ModelConversionSettings,
        log_dir: Path,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._log_dir = log_dir
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)
        self._tasks: set[asyncio.Task] = set()
        self._scheduled_ids: set[int] = set()
        self._processes: dict[int, asyncio.subprocess.Process] = {}
        self._closing = False

    async def start(self) -> None:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        session = self._session_factory()
        try:
            running = list(
                session.scalars(
                    select(ModelConversionModel).where(
                        ModelConversionModel.status == "running"
                    )
                )
            )
            now = datetime.now(timezone.utc)
            for item in running:
                item.status = "failed"
                item.finished_at = now
                item.error_message = "Backend restarted while conversion was running"
            queued_ids = list(
                session.scalars(
                    select(ModelConversionModel.id).where(
                        ModelConversionModel.status == "queued"
                    )
                )
            )
            session.commit()
        finally:
            session.close()
        for conversion_id in queued_ids:
            self.submit(conversion_id)

    def submit(self, conversion_id: int) -> None:
        if self._closing or conversion_id in self._scheduled_ids:
            return
        task = asyncio.create_task(self._run(conversion_id))
        self._scheduled_ids.add(conversion_id)
        self._tasks.add(task)
        task.add_done_callback(
            lambda completed, item_id=conversion_id: self._discard_task(
                completed, item_id
            )
        )

    async def shutdown(self) -> None:
        self._closing = True
        for process in self._processes.values():
            if process.returncode is None:
                process.terminate()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    def _discard_task(self, task: asyncio.Task, conversion_id: int) -> None:
        self._tasks.discard(task)
        self._scheduled_ids.discard(conversion_id)

    async def _run(self, conversion_id: int) -> None:
        async with self._semaphore:
            if self._closing:
                return
            session = self._session_factory()
            process_output_path: Path | None = None
            try:
                item = session.get(ModelConversionModel, conversion_id)
                if item is None or item.status != "queued":
                    return
                exp = session.get(ExpModel, item.exp_id)
                if exp is None:
                    raise RuntimeError("Experiment record was not found")
                runtime = self._settings.converters.get(item.converter_code)
                if runtime is None or not runtime.enabled:
                    raise RuntimeError(
                        "Converter '%s' is not enabled" % item.converter_code
                    )

                root = Path(exp.resolved_path).resolve()
                source_path = (root / item.source_file).resolve()
                output_path = (root / item.output_file).resolve()
                if not source_path.is_relative_to(root) or not source_path.is_file():
                    raise RuntimeError("Source model file was not found")
                if not output_path.is_relative_to(root):
                    raise RuntimeError("Output file must be under the experiment directory")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                process_output_path = output_path.with_name(
                    ".%s.conversion-%s.onnx" % (output_path.stem, item.id)
                )
                process_output_path.unlink(missing_ok=True)

                log_path = self._log_dir / ("%s.log" % item.id)
                item.status = "running"
                item.started_at = datetime.now(timezone.utc)
                item.log_path = str(log_path)
                item.error_message = None
                session.commit()

                command = self._build_command(
                    runtime=runtime,
                    source_path=source_path,
                    output_path=process_output_path,
                    params=json.loads(item.params_json or "{}"),
                )
                with log_path.open("ab") as log_handle:
                    process = await asyncio.create_subprocess_exec(
                        *command,
                        cwd=runtime.working_dir,
                        stdout=log_handle,
                        stderr=asyncio.subprocess.STDOUT,
                    )
                    self._processes[item.id] = process
                    return_code = await process.wait()
                    self._processes.pop(item.id, None)

                session.refresh(item)
                item.finished_at = datetime.now(timezone.utc)
                if return_code == 0 and process_output_path.is_file():
                    process_output_path.replace(output_path)
                    item.status = "succeeded"
                    item.result_files_json = json.dumps(
                        [item.output_file], ensure_ascii=True
                    )
                else:
                    process_output_path.unlink(missing_ok=True)
                    item.status = "failed"
                    item.error_message = self._failure_message(
                        log_path, return_code=return_code
                    )
                session.commit()
            except Exception as exc:
                session.rollback()
                if process_output_path is not None:
                    process_output_path.unlink(missing_ok=True)
                self._mark_failed(conversion_id, str(exc))
            finally:
                self._processes.pop(conversion_id, None)
                session.close()

    def _build_command(
        self, *, runtime, source_path: Path, output_path: Path, params: dict[str, Any]
    ) -> list[str]:
        command = [
            runtime.python_path,
            runtime.script_path,
            "--format",
            "onnx",
            "--model",
            str(source_path),
            "--output",
            str(output_path),
            "--device",
            str(params["device"]),
            "--imgsz",
            str(params["imgsz"]),
            "--opset",
            str(params["opset"]),
        ]
        if params.get("simplify"):
            command.append("--simplify")
        if params.get("dynamo"):
            command.append("--dynamo")
        return command

    def _failure_message(self, log_path: Path, *, return_code: int) -> str:
        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""
        tail = content[-4000:].strip()
        prefix = "Conversion process exited with code %s" % return_code
        return "%s\n%s" % (prefix, tail) if tail else prefix

    def _mark_failed(self, conversion_id: int, message: str) -> None:
        session = self._session_factory()
        try:
            item = session.get(ModelConversionModel, conversion_id)
            if item is None:
                return
            item.status = "failed"
            item.finished_at = datetime.now(timezone.utc)
            item.error_message = message[-4000:]
            session.commit()
        finally:
            session.close()
