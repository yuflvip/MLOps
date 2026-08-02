import asyncio
import json
from pathlib import Path

import pytest

from app.application.services.model_conversion_service import ModelConversionService
from app.domain.common.exceptions import ExpValidationError
from app.infrastructure.config.settings import (
    ModelConversionSettings,
    ModelConverterRuntimeSettings,
)
from app.infrastructure.db import Base, build_session_factory
from app.infrastructure.db.models import (
    ExpModel,
    ModelConversionModel,
    ProjectModel,
    QuantizationDatasetModel,
)
from app.infrastructure.model_conversion import LocalModelConversionScheduler
from app.infrastructure.repositories import (
    ExpRepository,
    ModelConversionRepository,
    ProjectRepository,
    QuantizationDatasetRepository,
)


class FakeScheduler:
    def __init__(self) -> None:
        self.submitted = []

    def submit(self, conversion_id: int) -> None:
        self.submitted.append(conversion_id)


def build_service(tmp_path: Path, architecture: str = "HGNetV2"):
    session_factory = build_session_factory("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(session_factory.kw["bind"])
    session = session_factory()
    project = ProjectModel(
        project="vehicle-classifier",
        name="Vehicle Classifier",
        model_type="classification",
        model_architecture=architecture,
        exp_root_path=str(tmp_path),
        dataset_ids_json="[]",
    )
    session.add(project)
    session.flush()
    exp_root = tmp_path / "exp-1"
    exp_root.mkdir()
    exp = ExpModel(
        project_id=project.id,
        name="exp-1",
        relative_path="exp-1",
        resolved_path=str(exp_root),
        review_status="pending_review",
    )
    session.add(exp)
    session.commit()

    scheduler = FakeScheduler()
    settings = ModelConversionSettings(
        converters={
            "hgnet_to_onnx": ModelConverterRuntimeSettings(
                enabled=True,
                python_path="/env/bin/python",
                working_dir="/model",
                script_path="/model/tools/export.py",
            ),
            "onnx_to_hisi3403": ModelConverterRuntimeSettings(
                enabled=True,
                python_path="/usr/bin/bash",
                working_dir="/converter/hisi3403",
                script_path="/converter/hisi3403/export_svpnnn_om.sh",
            ),
            "onnx_to_hisi3403_ascend_nnn": ModelConverterRuntimeSettings(
                enabled=True,
                python_path="/usr/bin/bash",
                working_dir="/converter/hisi3403/ascend_nnn",
                script_path="/converter/hisi3403/ascend_nnn/export_nnn_om.sh",
            ),
        }
    )
    service = ModelConversionService(
        conversion_repository=ModelConversionRepository(session),
        exp_repository=ExpRepository(session),
        project_repository=ProjectRepository(session),
        quantization_dataset_repository=QuantizationDatasetRepository(session),
        settings=settings,
        scheduler=scheduler,
    )
    return session, service, scheduler, exp, exp_root


def test_create_hgnet_onnx_conversion(tmp_path: Path):
    session, service, scheduler, exp, exp_root = build_service(tmp_path)
    (exp_root / "best.pth").write_bytes(b"checkpoint")

    result = service.create_conversion(
        exp.id,
        converter_code="hgnet_to_onnx",
        source_file="best.pth",
        output_file="best.onnx",
        params={"device": "cpu", "imgsz": "224", "opset": 13},
    )

    assert result["status"] == "queued"
    assert result["source_format"] == "pth"
    assert result["target_format"] == "onnx"
    assert result["created_at"].endswith("+00:00")
    assert result["params"] == {
        "device": "cpu",
        "dynamo": False,
        "imgsz": "224",
        "opset": 13,
        "overwrite": False,
        "simplify": False,
    }
    assert scheduler.submitted == [result["id"]]
    session.close()


def test_create_conversion_rejects_non_hgnet_architecture(tmp_path: Path):
    session, service, scheduler, exp, exp_root = build_service(
        tmp_path, architecture="YOLOv8"
    )
    (exp_root / "best.pth").write_bytes(b"checkpoint")

    with pytest.raises(ExpValidationError, match="does not support architecture"):
        service.create_conversion(
            exp.id,
            converter_code="hgnet_to_onnx",
            source_file="best.pth",
            output_file="best.onnx",
            params={},
        )

    assert scheduler.submitted == []
    session.close()


def test_create_conversion_rejects_path_outside_exp(tmp_path: Path):
    session, service, scheduler, exp, _exp_root = build_service(tmp_path)
    (tmp_path / "outside.pth").write_bytes(b"checkpoint")

    with pytest.raises(ExpValidationError, match="under the exp directory"):
        service.create_conversion(
            exp.id,
            converter_code="hgnet_to_onnx",
            source_file="../outside.pth",
            output_file="best.onnx",
            params={},
        )

    assert scheduler.submitted == []
    session.close()


def test_create_conversion_allows_existing_output_when_overwrite_is_enabled(
    tmp_path: Path,
):
    session, service, scheduler, exp, exp_root = build_service(tmp_path)
    (exp_root / "best.pth").write_bytes(b"checkpoint")
    (exp_root / "best.onnx").write_bytes(b"previous model")

    result = service.create_conversion(
        exp.id,
        converter_code="hgnet_to_onnx",
        source_file="best.pth",
        output_file="best.onnx",
        params={"overwrite": True},
    )

    assert result["params"]["overwrite"] is True
    assert scheduler.submitted == [result["id"]]
    session.close()


def test_create_hisi3403_conversion_keeps_all_parameters(tmp_path: Path):
    session, service, scheduler, exp, exp_root = build_service(
        tmp_path, architecture="YOLOv8"
    )
    (exp_root / "best.onnx").write_bytes(b"onnx")
    dataset_root = tmp_path / "quantization"
    dataset_root.mkdir()
    image_list = dataset_root / "ref_img_list.txt"
    image_list.write_text("/data/calibration.jpg\n", encoding="utf-8")
    dataset = QuantizationDatasetModel(
        name="3403量化集",
        storage_path=str(dataset_root),
        image_count=1,
        size_bytes=10,
    )
    session.add(dataset)
    session.commit()

    result = service.create_conversion(
        exp.id,
        converter_code="onnx_to_hisi3403",
        source_file="best.onnx",
        output_file="best.om",
        params={
            "quantization_dataset_id": dataset.id,
            "input_shape": "images:1,3,640,640",
            "insert_op_conf": "insert_op.cfg",
            "soc_version": "SS928V100",
            "compile_mode": "6",
            "output_type": "FP32",
            "quant_mode": "1",
            "high_precision_layer": "/model.22/Concat_5",
            "online_model_type": "0",
            "dry_run": True,
            "overwrite": True,
        },
    )

    assert result["source_format"] == "onnx"
    assert result["target_platform"] == "hisi3403"
    assert result["target_format"] == "om"
    assert result["params"]["quantization_dataset_name"] == "3403量化集"
    assert result["params"]["image_list_path"] == str(image_list)
    assert result["params"]["input_shape"] == "images:1,3,640,640"
    assert result["params"]["dry_run"] is True
    assert scheduler.submitted == [result["id"]]
    session.close()


def test_hisi3403_dry_run_finishes_without_om_file(tmp_path: Path):
    session_factory = build_session_factory("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(session_factory.kw["bind"])
    session = session_factory()
    project = ProjectModel(
        project="dry-run",
        name="Dry Run",
        model_type="classification",
        model_architecture="HGNetV2",
        dataset_ids_json="[]",
    )
    session.add(project)
    session.flush()
    exp_root = tmp_path / "exp"
    exp_root.mkdir()
    (exp_root / "best.onnx").write_bytes(b"onnx")
    exp = ExpModel(
        project_id=project.id,
        name="exp",
        relative_path="exp",
        resolved_path=str(exp_root),
        review_status="pending_review",
    )
    session.add(exp)
    session.flush()
    image_list = tmp_path / "ref_img_list.txt"
    image_list.write_text("/tmp/calibration.jpg\n", encoding="utf-8")
    script_dir = Path(__file__).resolve().parents[1] / (
        "scripts/model_conversion/hisi3403/svp_nnn"
    )
    params = {
        "image_list_path": str(image_list),
        "input_shape": "images:1,3,224,224",
        "insert_op_conf": "insert_op_hgnet.cfg",
        "soc_version": "SS928V100",
        "compile_mode": "6",
        "output_type": "FP32",
        "quant_mode": "1",
        "high_precision_layer": "",
        "online_model_type": "0",
        "dry_run": True,
        "overwrite": False,
    }
    conversion = ModelConversionModel(
        exp_id=exp.id,
        converter_code="onnx_to_hisi3403",
        source_file="best.onnx",
        source_format="onnx",
        target_platform="hisi3403",
        target_format="om",
        output_file="best.om",
        status="queued",
        params_json=json.dumps(params),
        result_files_json="[]",
    )
    session.add(conversion)
    session.commit()
    conversion_id = conversion.id
    session.close()

    settings = ModelConversionSettings(
        converters={
            "onnx_to_hisi3403": ModelConverterRuntimeSettings(
                enabled=True,
                python_path="/usr/bin/bash",
                working_dir=str(script_dir),
                script_path=str(script_dir / "export_svpnnn_om.sh"),
            )
        }
    )
    scheduler = LocalModelConversionScheduler(
        session_factory=session_factory,
        settings=settings,
        log_dir=tmp_path / "logs",
    )
    asyncio.run(scheduler._run(conversion_id))

    session = session_factory()
    saved = session.get(ModelConversionModel, conversion_id)
    assert saved is not None
    assert saved.status == "succeeded"
    assert json.loads(saved.result_files_json) == []
    assert saved.log_path == "best.onnx-haisi3403.log"
    log_path = exp_root / "best.onnx-haisi3403.log"
    assert log_path.is_file()
    assert "dry-run完成" in log_path.read_text(encoding="utf-8")
    assert not (exp_root / "best.om").exists()
    session.close()


def test_create_ascend_nnn_conversion_does_not_require_dataset(tmp_path: Path):
    session, service, scheduler, exp, exp_root = build_service(tmp_path)
    (exp_root / "best.onnx").write_bytes(b"onnx")

    result = service.create_conversion(
        exp.id,
        converter_code="onnx_to_hisi3403_ascend_nnn",
        source_file="best.onnx",
        output_file="hisi_atc_output_nnn/best.om",
        params={
            "input_shape": "images:1,3,224,224",
            "insert_op_conf": "insert_op_nnn_hgnet.cfg",
            "soc_version": "OPTG",
            "enable_single_stream": True,
            "enable_small_channel": 1,
            "overwrite": True,
        },
    )

    assert result["target_platform"] == "hisi3403"
    assert result["params"]["soc_version"] == "OPTG"
    assert result["params"]["enable_single_stream"] is True
    assert "quantization_dataset_id" not in result["params"]
    assert scheduler.submitted == [result["id"]]
    session.close()


def test_ascend_nnn_dry_run_uses_named_script(tmp_path: Path):
    session_factory = build_session_factory("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(session_factory.kw["bind"])
    session = session_factory()
    project = ProjectModel(
        project="ascend-nnn",
        name="Ascend NNN",
        model_type="classification",
        model_architecture="HGNetV2",
        dataset_ids_json="[]",
    )
    session.add(project)
    session.flush()
    exp_root = tmp_path / "exp"
    exp_root.mkdir()
    (exp_root / "best.onnx").write_bytes(b"onnx")
    exp = ExpModel(
        project_id=project.id,
        name="exp",
        relative_path="exp",
        resolved_path=str(exp_root),
        review_status="pending_review",
    )
    session.add(exp)
    session.flush()
    params = {
        "input_shape": "images:1,3,224,224",
        "insert_op_conf": "insert_op_nnn_hgnet.cfg",
        "soc_version": "OPTG",
        "enable_single_stream": True,
        "enable_small_channel": 1,
        "dry_run": True,
        "overwrite": False,
    }
    conversion = ModelConversionModel(
        exp_id=exp.id,
        converter_code="onnx_to_hisi3403_ascend_nnn",
        source_file="best.onnx",
        source_format="onnx",
        target_platform="hisi3403",
        target_format="om",
        output_file="hisi_atc_output_nnn/best.om",
        status="queued",
        params_json=json.dumps(params),
        result_files_json="[]",
    )
    session.add(conversion)
    session.commit()
    conversion_id = conversion.id
    session.close()

    script_dir = Path(__file__).resolve().parents[1] / (
        "scripts/model_conversion/hisi3403/ascend_nnn"
    )
    settings = ModelConversionSettings(
        converters={
            "onnx_to_hisi3403_ascend_nnn": ModelConverterRuntimeSettings(
                enabled=True,
                python_path="/usr/bin/bash",
                working_dir=str(script_dir),
                script_path=str(script_dir / "export_nnn_om.sh"),
            )
        }
    )
    scheduler = LocalModelConversionScheduler(
        session_factory=session_factory,
        settings=settings,
        log_dir=tmp_path / "logs",
    )
    asyncio.run(scheduler._run(conversion_id))

    session = session_factory()
    saved = session.get(ModelConversionModel, conversion_id)
    assert saved is not None
    assert saved.status == "succeeded"
    assert saved.log_path == "hisi_atc_output_nnn/best.onnx-haisi3403-ascend-nnn.log"
    log_path = exp_root / saved.log_path
    assert "export_nnn_om.sh" in log_path.read_text(encoding="utf-8")
    assert "dry-run完成" in log_path.read_text(encoding="utf-8")
    assert not (exp_root / "hisi_atc_output_nnn/best.om").exists()
    session.close()
