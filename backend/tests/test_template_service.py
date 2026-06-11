from pathlib import Path

import pytest

from app.application.services.template_service import TemplateService


BACKEND_ROOT = Path(__file__).resolve().parents[1]
from app.domain.common.exceptions import (
    TemplateNotFoundError,
    TemplateValidationError,
)


def test_template_service_loads_yolo_default_template():
    service = TemplateService(BACKEND_ROOT / "config" / "training-templates.yaml")

    template = service.get_template("yolo-default")

    assert template["name"] == "yolo-default"
    assert template["runtime"]["adapter"] == "training"


def test_template_service_loads_convnext_default_template():
    service = TemplateService(BACKEND_ROOT / "config" / "training-templates.yaml")

    template = service.get_template("convnext-default")

    assert template["name"] == "convnext-default"
    assert template.get("entrypoint") is None
    assert template["runtime"]["launcher"] == "torchrun"
    assert template["runtime"]["adapter"] == "training"
    assert template["runtime"]["script_path"] == (
        "/mnt/sdb/yufl/cnn/ConvNext/convnext_cls/tools/train.py"
    )
    assert template["execution_defaults"] == {
        "cuda_visible_devices": "2",
        "nproc_per_node": 1,
    }


def test_template_service_raises_for_unknown_template():
    service = TemplateService(BACKEND_ROOT / "config" / "training-templates.yaml")

    with pytest.raises(TemplateNotFoundError):
        service.get_template("missing-template")


def test_template_service_rejects_invalid_document_shape(tmp_path):
    template_path = tmp_path / "training-templates.yaml"
    template_path.write_text("- invalid\n", encoding="utf-8")

    with pytest.raises(TemplateValidationError, match="top-level mapping"):
        TemplateService(template_path)


def test_template_service_rejects_duplicate_template_names(tmp_path):
    template_path = tmp_path / "training-templates.yaml"
    template_path.write_text(
        """
templates:
  - name: duplicate
    queue: queue-a
    runtime:
      adapter: generic
      launcher: python
      script_path: train.py
  - name: duplicate
    queue: queue-b
    runtime:
      adapter: generic
      launcher: python
      script_path: train.py
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(TemplateValidationError, match="Duplicate template name"):
        TemplateService(template_path)


def test_template_service_rejects_missing_runtime_adapter(tmp_path):
    template_path = tmp_path / "training-templates.yaml"
    template_path.write_text(
        """
templates:
  - name: missing-adapter
    runtime:
      launcher: python
      script_path: train.py
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(TemplateValidationError, match="runtime.adapter"):
        TemplateService(template_path)


def test_template_service_rejects_unsupported_runtime_adapter(tmp_path):
    template_path = tmp_path / "training-templates.yaml"
    template_path.write_text(
        """
templates:
  - name: bad-adapter
    runtime:
      adapter: unknown
      launcher: python
      script_path: train.py
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(TemplateValidationError, match="not supported"):
        TemplateService(template_path)


def test_template_service_preserves_template_extension_fields(tmp_path):
    template_path = tmp_path / "training-templates.yaml"
    template_path.write_text(
        """
templates:
  - name: custom-template
    display_name: Custom Template
    queue: queue-a
    entrypoint: python train.py
    project: cv/project-a
    runtime:
      adapter: generic
      launcher: python
      script_path: train.py
    tags:
      - yolo
      - baseline
    defaults:
      epochs: 10
""".strip(),
        encoding="utf-8",
    )

    service = TemplateService(template_path)

    template = service.get_template("custom-template")

    assert template["project"] == "cv/project-a"
    assert template["tags"] == ["yolo", "baseline"]
    assert template["runtime"]["adapter"] == "generic"
