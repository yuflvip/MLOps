import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from app.domain.common.exceptions import (
    ExpConflictError,
    ExpNotFoundError,
    ExpValidationError,
)
from app.infrastructure.config.settings import ModelConversionSettings
from app.infrastructure.db.models import ModelConversionModel
from app.infrastructure.repositories import (
    ExpRepository,
    ModelConversionRepository,
    ProjectRepository,
    QuantizationDatasetRepository,
)


CONVERTER_METADATA = {
    "hgnet_to_onnx": {
        "source_formats": {"pt", "pth"},
        "target_platform": "onnx",
        "target_format": "onnx",
        "architectures": {"hgnetv2"},
    },
    "onnx_to_hisi3403": {
        "source_formats": {"onnx"},
        "target_platform": "hisi3403",
        "target_format": "om",
        "architectures": None,
    },
    "onnx_to_hisi3403_ascend_nnn": {
        "source_formats": {"onnx"},
        "target_platform": "hisi3403",
        "target_format": "om",
        "architectures": None,
    },
}


def _isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def serialize_model_conversion(item: ModelConversionModel) -> Dict[str, Any]:
    return {
        "id": item.id,
        "exp_id": item.exp_id,
        "parent_conversion_id": item.parent_conversion_id,
        "converter_code": item.converter_code,
        "source_file": item.source_file,
        "source_format": item.source_format,
        "target_platform": item.target_platform,
        "target_format": item.target_format,
        "output_file": item.output_file,
        "status": item.status,
        "params": json.loads(item.params_json or "{}"),
        "result_files": json.loads(item.result_files_json or "[]"),
        "log_path": item.log_path,
        "error_message": item.error_message,
        "created_at": _isoformat_utc(item.created_at),
        "started_at": _isoformat_utc(item.started_at),
        "finished_at": _isoformat_utc(item.finished_at),
    }


class ModelConversionService:
    def __init__(
        self,
        *,
        conversion_repository: ModelConversionRepository,
        exp_repository: ExpRepository,
        project_repository: ProjectRepository,
        quantization_dataset_repository: QuantizationDatasetRepository,
        settings: ModelConversionSettings,
        scheduler,
    ) -> None:
        self._conversion_repository = conversion_repository
        self._exp_repository = exp_repository
        self._project_repository = project_repository
        self._quantization_dataset_repository = quantization_dataset_repository
        self._settings = settings
        self._scheduler = scheduler

    def create_conversion(
        self,
        exp_id: int,
        *,
        converter_code: str,
        source_file: str,
        output_file: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        exp = self._exp_repository.get_by_id(exp_id)
        if exp is None:
            raise ExpNotFoundError("Exp '%s' was not found" % exp_id)

        metadata = CONVERTER_METADATA.get(converter_code)
        runtime = self._settings.converters.get(converter_code)
        if metadata is None or runtime is None or not runtime.enabled:
            raise ExpValidationError("Model converter '%s' is not available" % converter_code)

        project = self._project_repository.get_by_id(exp.project_id)
        architecture = (project.model_architecture if project else "") or ""
        supported_architectures = metadata["architectures"]
        if (
            supported_architectures is not None
            and architecture.casefold() not in supported_architectures
        ):
            raise ExpValidationError(
                "Converter '%s' does not support architecture '%s'"
                % (converter_code, architecture or "unknown")
            )

        root = Path(exp.resolved_path).resolve()
        if not root.is_dir():
            raise ExpValidationError("Exp directory does not exist or is not a directory")
        source_path, normalized_source = self._resolve_path(
            root, source_file, must_exist=True
        )
        source_format = source_path.suffix.lower().removeprefix(".")
        if source_format not in metadata["source_formats"]:
            allowed_formats = ", ".join(
                ".%s" % value for value in sorted(metadata["source_formats"])
            )
            raise ExpValidationError("Source model must be one of: %s" % allowed_formats)

        output_path, normalized_output = self._resolve_path(
            root, output_file, must_exist=False
        )
        expected_suffix = ".%s" % metadata["target_format"]
        if output_path.suffix.lower() != expected_suffix:
            raise ExpValidationError(
                "Output file must use the %s extension" % expected_suffix
            )
        if converter_code == "hgnet_to_onnx":
            normalized_params = self._validate_hgnet_params(params)
        elif converter_code == "onnx_to_hisi3403_ascend_nnn":
            normalized_params = self._validate_ascend_nnn_params(params)
        else:
            normalized_params = self._validate_hisi3403_params(params)
        if (
            output_path.exists()
            and not normalized_params["overwrite"]
            and not normalized_params.get("dry_run", False)
        ):
            raise ExpConflictError(
                "输出文件“%s”已存在，请勾选覆盖同名文件或修改输出文件名"
                % normalized_output
            )
        if self._conversion_repository.get_active_by_output(exp_id, normalized_output):
            raise ExpConflictError(
                "输出文件“%s”已有转换任务正在执行" % normalized_output
            )

        saved = self._conversion_repository.add(
            ModelConversionModel(
                exp_id=exp.id,
                converter_code=converter_code,
                source_file=normalized_source,
                source_format=source_format,
                target_platform=metadata["target_platform"],
                target_format=metadata["target_format"],
                output_file=normalized_output,
                status="queued",
                params_json=json.dumps(normalized_params, ensure_ascii=True, sort_keys=True),
                result_files_json="[]",
            )
        )
        self._conversion_repository.commit()
        self._scheduler.submit(saved.id)
        return serialize_model_conversion(saved)

    def list_conversions(self, exp_id: int) -> Dict[str, Any]:
        if self._exp_repository.get_by_id(exp_id) is None:
            raise ExpNotFoundError("Exp '%s' was not found" % exp_id)
        items = self._conversion_repository.list_by_exp(exp_id)
        return {
            "items": [serialize_model_conversion(item) for item in items],
            "total": len(items),
        }

    def get_conversion(self, conversion_id: int) -> Dict[str, Any]:
        item = self._conversion_repository.get_by_id(conversion_id)
        if item is None:
            raise ExpNotFoundError(
                "Model conversion '%s' was not found" % conversion_id
            )
        return serialize_model_conversion(item)

    def _resolve_path(
        self, root: Path, relative_path: str, *, must_exist: bool
    ) -> tuple[Path, str]:
        raw_path = Path(relative_path.strip())
        if not relative_path.strip() or raw_path.is_absolute():
            raise ExpValidationError("Conversion file path must be relative")
        resolved = (root / raw_path).resolve()
        if not resolved.is_relative_to(root):
            raise ExpValidationError("Conversion file must be under the exp directory")
        if must_exist and not resolved.is_file():
            raise ExpValidationError("Source model file was not found")
        return resolved, resolved.relative_to(root).as_posix()

    def _validate_hgnet_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {"device", "imgsz", "opset", "simplify", "dynamo", "overwrite"}
        unknown = set(params) - allowed
        if unknown:
            raise ExpValidationError(
                "Unsupported conversion parameters: %s" % ", ".join(sorted(unknown))
            )
        device = str(params.get("device", "cpu")).lower()
        if device not in {"cpu", "cuda"}:
            raise ExpValidationError("device must be cpu or cuda")
        imgsz = str(params.get("imgsz", "224")).strip()
        parts = [part.strip() for part in imgsz.split(",") if part.strip()]
        try:
            sizes = [int(part) for part in parts]
        except ValueError as exc:
            raise ExpValidationError("imgsz must be a positive integer or h,w") from exc
        if len(sizes) not in {1, 2} or any(size <= 0 for size in sizes):
            raise ExpValidationError("imgsz must be a positive integer or h,w")
        opset = params.get("opset", 13)
        if isinstance(opset, bool) or not isinstance(opset, int) or not 7 <= opset <= 21:
            raise ExpValidationError("opset must be an integer between 7 and 21")
        return {
            "device": device,
            "imgsz": ",".join(str(size) for size in sizes),
            "opset": opset,
            "simplify": bool(params.get("simplify", False)),
            "dynamo": bool(params.get("dynamo", False)),
            "overwrite": bool(params.get("overwrite", False)),
        }

    def _validate_hisi3403_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {
            "quantization_dataset_id",
            "input_shape",
            "insert_op_conf",
            "soc_version",
            "compile_mode",
            "output_type",
            "quant_mode",
            "high_precision_layer",
            "online_model_type",
            "dry_run",
            "overwrite",
        }
        unknown = set(params) - allowed
        if unknown:
            raise ExpValidationError(
                "Unsupported conversion parameters: %s" % ", ".join(sorted(unknown))
            )

        dataset_id = params.get("quantization_dataset_id")
        if isinstance(dataset_id, bool) or not isinstance(dataset_id, int):
            raise ExpValidationError("quantization_dataset_id must be an integer")
        dataset = self._quantization_dataset_repository.get_by_id(dataset_id)
        if dataset is None:
            raise ExpValidationError("Quantization dataset was not found")
        if dataset.image_count <= 0:
            raise ExpValidationError("量化数据集没有图片，不能执行转换")
        image_list_path = Path(dataset.storage_path) / "ref_img_list.txt"
        if not image_list_path.is_file():
            raise ExpValidationError("量化数据集的 ref_img_list.txt 不存在")

        input_shape = self._optional_text(
            params.get("input_shape"), name="input_shape", max_length=255
        )
        if input_shape and not re.fullmatch(
            r"[^:,\s]+:\d+,\d+,\d+,\d+", input_shape
        ):
            raise ExpValidationError(
                "input_shape must use input_name:n,c,h,w format"
            )

        insert_op_conf = str(params.get("insert_op_conf", "insert_op.cfg")).strip()
        if insert_op_conf not in {"insert_op.cfg", "insert_op_hgnet.cfg"}:
            raise ExpValidationError("insert_op_conf is not supported")

        return {
            "quantization_dataset_id": dataset.id,
            "quantization_dataset_name": dataset.name,
            "image_list_path": str(image_list_path.resolve()),
            "input_shape": input_shape,
            "insert_op_conf": insert_op_conf,
            "soc_version": self._required_text(
                params.get("soc_version", "SS928V100"),
                name="soc_version",
                max_length=64,
            ),
            "compile_mode": self._required_text(
                params.get("compile_mode", "6"),
                name="compile_mode",
                max_length=32,
            ),
            "output_type": self._optional_text(
                params.get("output_type", "FP32"),
                name="output_type",
                max_length=32,
            ),
            "quant_mode": self._required_text(
                params.get("quant_mode", "1"),
                name="quant_mode",
                max_length=32,
            ),
            "high_precision_layer": self._optional_text(
                params.get("high_precision_layer"),
                name="high_precision_layer",
                max_length=512,
            ),
            "online_model_type": self._required_text(
                params.get("online_model_type", "0"),
                name="online_model_type",
                max_length=32,
            ),
            "dry_run": bool(params.get("dry_run", False)),
            "overwrite": bool(params.get("overwrite", False)),
        }

    def _validate_ascend_nnn_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {
            "input_shape",
            "insert_op_conf",
            "soc_version",
            "enable_single_stream",
            "enable_small_channel",
            "dry_run",
            "overwrite",
        }
        unknown = set(params) - allowed
        if unknown:
            raise ExpValidationError(
                "Unsupported conversion parameters: %s" % ", ".join(sorted(unknown))
            )

        input_shape = self._required_text(
            params.get("input_shape"), name="input_shape", max_length=255
        )
        if not re.fullmatch(r"[^:,\s]+:\d+,\d+,\d+,\d+", input_shape):
            raise ExpValidationError(
                "input_shape must use input_name:n,c,h,w format"
            )

        insert_op_conf = str(
            params.get("insert_op_conf", "insert_op_nnn_hgnet.cfg")
        ).strip()
        if insert_op_conf not in {"insert_op_nnn_hgnet.cfg"}:
            raise ExpValidationError("insert_op_conf is not supported")

        enable_single_stream = params.get("enable_single_stream", True)
        if not isinstance(enable_single_stream, bool):
            raise ExpValidationError("enable_single_stream must be a boolean")
        enable_small_channel = params.get("enable_small_channel", 1)
        if isinstance(enable_small_channel, bool) or enable_small_channel not in {0, 1}:
            raise ExpValidationError("enable_small_channel must be 0 or 1")

        return {
            "input_shape": input_shape,
            "insert_op_conf": insert_op_conf,
            "soc_version": self._required_text(
                params.get("soc_version", "OPTG"),
                name="soc_version",
                max_length=64,
            ),
            "enable_single_stream": enable_single_stream,
            "enable_small_channel": enable_small_channel,
            "dry_run": bool(params.get("dry_run", False)),
            "overwrite": bool(params.get("overwrite", False)),
        }

    @staticmethod
    def _required_text(value: Any, *, name: str, max_length: int) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ExpValidationError("%s must not be empty" % name)
        if len(normalized) > max_length or "\x00" in normalized:
            raise ExpValidationError("%s is invalid" % name)
        return normalized

    @classmethod
    def _optional_text(cls, value: Any, *, name: str, max_length: int) -> str:
        if value is None:
            return ""
        normalized = str(value).strip()
        if not normalized:
            return ""
        return cls._required_text(normalized, name=name, max_length=max_length)
