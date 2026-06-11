from typing import Any, Dict, List, Mapping

from app.domain.common.exceptions import TemplateValidationError

ALLOWED_RUNTIME_ADAPTERS = {"generic", "training", "onnx_export"}


def validate_template_payload(template: Mapping[str, Any]) -> None:
    if not isinstance(template, Mapping):
        raise TemplateValidationError("Template entry must be a mapping")
    if not template.get("name"):
        raise TemplateValidationError("Template entry must define a non-empty name")
    runtime = template.get("runtime")
    if not isinstance(runtime, Mapping):
        raise TemplateValidationError("Template entry must define 'runtime' as a mapping")
    adapter = runtime.get("adapter")
    if not isinstance(adapter, str) or not adapter:
        raise TemplateValidationError("Template runtime.adapter must be a non-empty string")
    if adapter not in ALLOWED_RUNTIME_ADAPTERS:
        raise TemplateValidationError(
            "Template runtime.adapter '%s' is not supported" % adapter
        )


def validate_templates_document(document: Any) -> List[Dict[str, Any]]:
    if not isinstance(document, Mapping):
        raise TemplateValidationError("Template document must be a top-level mapping")

    raw_templates = document.get("templates")
    if not isinstance(raw_templates, list):
        raise TemplateValidationError("Template document must define 'templates' as a list")

    templates: List[Dict[str, Any]] = []
    seen_names = set()
    for raw_template in raw_templates:
        validate_template_payload(raw_template)
        template_name = str(raw_template["name"])
        if template_name in seen_names:
            raise TemplateValidationError(
                "Duplicate template name '%s' found in template document"
                % template_name
            )
        seen_names.add(template_name)
        templates.append(dict(raw_template))
    return templates
