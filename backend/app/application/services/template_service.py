from pathlib import Path
from typing import Any, Dict, List

from app.application.dto.training import TrainingTemplateDTO
from app.domain.common.exceptions import TemplateNotFoundError
from app.infrastructure.template.renderer import load_templates_document
from app.infrastructure.template.validator import validate_templates_document


class TemplateService:
    def __init__(self, template_path: Path):
        self._template_path = template_path
        self._templates = self._load_templates()

    def list_templates(self) -> List[Dict[str, Any]]:
        return [template.copy() for template in self._templates]

    def get_template(self, template_name: str) -> Dict[str, Any]:
        for template in self._templates:
            if template["name"] == template_name:
                return template.copy()
        raise TemplateNotFoundError(
            "Template '%s' not found in %s" % (template_name, self._template_path)
        )

    def get_template_dto(self, template_name: str) -> TrainingTemplateDTO:
        return TrainingTemplateDTO.model_validate(self.get_template(template_name))

    def _load_templates(self) -> List[Dict[str, Any]]:
        document = load_templates_document(self._template_path)
        raw_templates = validate_templates_document(document)
        return [
            TrainingTemplateDTO.model_validate(raw_template).model_dump()
            for raw_template in raw_templates
        ]
