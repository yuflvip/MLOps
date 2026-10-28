import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
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
            process_source_path: Path | None = None
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
                    ".%s.conversion-%s.%s"
                    % (output_path.stem, item.id, item.target_format)
                )
                process_output_path.unlink(missing_ok=True)

                command_source_path = source_path
                if item.converter_code == "yolo_to_onnx":
                    process_source_path = process_output_path.with_suffix(
                        source_path.suffix
                    )
                    process_source_path.unlink(missing_ok=True)
                    try:
                        os.link(source_path, process_source_path)
                    except OSError:
                        shutil.copy2(source_path, process_source_path)
                    command_source_path = process_source_path

                if item.converter_code in {
                    "onnx_to_hisi3403",
                    "onnx_to_hisi3403_ascend_nnn",
                }:
                    log_suffix = (
                        "haisi3403"
                        if item.converter_code == "onnx_to_hisi3403"
                        else "haisi3403-ascend-nnn"
                    )
                    log_path = output_path.with_name(
                        "%s.onnx-%s.log" % (output_path.stem, log_suffix)
                    )
                    stored_log_path = log_path.relative_to(root).as_posix()
                    log_mode = "wb"
                else:
                    log_path = self._log_dir / ("%s.log" % item.id)
                    stored_log_path = str(log_path)
                    log_mode = "ab"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                item.status = "running"
                item.started_at = datetime.now(timezone.utc)
                item.log_path = stored_log_path
                item.error_message = None
                session.commit()

                command = self._build_command(
                    converter_code=item.converter_code,
                    runtime=runtime,
                    source_path=command_source_path,
                    output_path=process_output_path,
                    params=json.loads(item.params_json or "{}"),
                )
                with log_path.open(log_mode) as log_handle:
                    header = (
                        "转换任务ID: %s\n"
                        "开始时间: %s\n"
                        "源模型: %s\n"
                        "目标模型: %s\n"
                        "执行命令: %s\n\n"
                        % (
                            item.id,
                            item.started_at.isoformat(),
                            source_path,
                            output_path,
                            shlex.join(command),
                        )
                    )
                    log_handle.write(header.encode("utf-8"))
                    log_handle.flush()
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
                params = json.loads(item.params_json or "{}")
                if return_code == 0 and params.get("dry_run"):
                    process_output_path.unlink(missing_ok=True)
                    item.status = "succeeded"
                    item.result_files_json = "[]"
                elif return_code == 0 and process_output_path.is_file():
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
                if process_source_path is not None:
                    process_source_path.unlink(missing_ok=True)
                self._processes.pop(conversion_id, None)
                session.close()

    def _build_command(
        self,
        *,
        converter_code: str,
        runtime,
        source_path: Path,
        output_path: Path,
        params: dict[str, Any],
    ) -> list[str]:
        if converter_code == "onnx_to_hisi3403":
            return self._build_hisi3403_command(
                runtime=runtime,
                source_path=source_path,
                output_path=output_path,
                params=params,
            )
        if converter_code == "onnx_to_hisi3403_ascend_nnn":
            return self._build_ascend_nnn_command(
                runtime=runtime,
                source_path=source_path,
                output_path=output_path,
                params=params,
            )
        if converter_code == "yolo_to_onnx":
            return self._build_yolo_command(
                runtime=runtime,
                source_path=source_path,
                params=params,
            )
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

    def _build_yolo_command(
        self, *, runtime, source_path: Path, params: dict[str, Any]
    ) -> list[str]:
        command = [
            runtime.python_path,
            "export",
            "model=%s" % source_path,
            "format=onnx",
            "imgsz=%s" % params["imgsz"],
            "end2end=%s" % str(params["end2end"]),
        ]
        if params.get("opset") is not None:
            command.append("opset=%s" % params["opset"])
        return command

    def _build_hisi3403_command(
        self, *, runtime, source_path: Path, output_path: Path, params: dict[str, Any]
    ) -> list[str]:
        image_list_path = Path(str(params["image_list_path"]))
        if not image_list_path.is_file():
            raise RuntimeError("Quantization image list was not found")
        insert_op_conf = Path(runtime.script_path).parent / "configs" / str(
            params["insert_op_conf"]
        )
        if not insert_op_conf.is_file():
            raise RuntimeError("AIPP config file was not found")

        command = [
            runtime.python_path,
            runtime.script_path,
            "--model",
            str(source_path),
            "--image_list",
            str(image_list_path),
            "--insert_op_conf",
            str(insert_op_conf),
            "--output",
            str(output_path.with_suffix("")),
            "--soc_version",
            str(params["soc_version"]),
            "--compile_mode",
            str(params["compile_mode"]),
            "--output_type",
            str(params["output_type"]),
            "--quant_mode",
            str(params["quant_mode"]),
            "--online_model_type",
            str(params["online_model_type"]),
            "--weight_quant_per_channel",
            str(params.get("weight_quant_per_channel", 1)),
            "--matmul_per_channel_enable",
            str(params.get("matmul_per_channel_enable", 1)),
            "--all_batch_quant_together_enable",
            str(params.get("all_batch_quant_together_enable", 1)),
            "--softmax_optimize_enable",
            str(params.get("softmax_optimize_enable", 1)),
        ]
        if params.get("input_shape"):
            command.extend(["--input_shape", str(params["input_shape"])])
        if params.get("high_precision_layer"):
            command.extend(
                ["--high_precision_layer", str(params["high_precision_layer"])]
            )
        if params.get("dry_run"):
            command.append("--dry-run")
        return command

    def _build_ascend_nnn_command(
        self, *, runtime, source_path: Path, output_path: Path, params: dict[str, Any]
    ) -> list[str]:
        insert_op_conf = Path(runtime.script_path).parent / "configs" / str(
            params["insert_op_conf"]
        )
        if not insert_op_conf.is_file():
            raise RuntimeError("AIPP config file was not found")

        command = [
            runtime.python_path,
            runtime.script_path,
            "--model",
            str(source_path),
            "--input_shape",
            str(params["input_shape"]),
            "--insert_op_conf",
            str(insert_op_conf),
            "--output",
            str(output_path.with_suffix("")),
            "--soc_version",
            str(params["soc_version"]),
            "--enable_single_stream",
            "true" if params["enable_single_stream"] else "false",
            "--enable_small_channel",
            str(params["enable_small_channel"]),
        ]
        if params.get("dry_run"):
            command.append("--dry-run")
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
