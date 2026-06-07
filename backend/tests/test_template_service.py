from pathlib import Path

import pytest

from app.application.services.template_service import TemplateService
from app.domain.common.exceptions import (
    TemplateNotFoundError,
    TemplateValidationError,
)


def test_template_service_loads_yolo_default_template():
    service = TemplateService(Path("config/training-templates.yaml"))

    template = service.get_template("yolo-default")

    assert template["name"] == "yolo-default"


def test_template_service_raises_for_unknown_template():
    service = TemplateService(Path("config/training-templates.yaml"))

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
  - name: duplicate
    queue: queue-b
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(TemplateValidationError, match="Duplicate template name"):
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
    tags:
      - yolo
      - baseline
    execution:
      working_dir: /workspace/project-a
    defaults:
      epochs: 10
""".strip(),
        encoding="utf-8",
    )

    service = TemplateService(template_path)

    template = service.get_template("custom-template")

    assert template["project"] == "cv/project-a"
    assert template["tags"] == ["yolo", "baseline"]
    assert template["execution"] == {"working_dir": "/workspace/project-a"}
