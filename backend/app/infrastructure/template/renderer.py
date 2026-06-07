from pathlib import Path
from typing import Any, Dict

import yaml


def load_templates_document(template_path: Path) -> Dict[str, Any]:
    content = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    if content is None:
        return {}
    return content
