from pathlib import Path

import pytest

from app.application.services.model_conversion_service import ModelConversionService
from app.domain.common.exceptions import ExpValidationError
from app.infrastructure.config.settings import (
    ModelConversionSettings,
    ModelConverterRuntimeSettings,
)
from app.infrastructure.db import Base, build_session_factory
from app.infrastructure.db.models import ExpModel, ProjectModel
from app.infrastructure.repositories import (
    ExpRepository,
    ModelConversionRepository,
    ProjectRepository,
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
            )
        }
    )
    service = ModelConversionService(
        conversion_repository=ModelConversionRepository(session),
        exp_repository=ExpRepository(session),
        project_repository=ProjectRepository(session),
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
