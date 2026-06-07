from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class TrainingTemplateDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    display_name: Optional[str] = None
    queue: Optional[str] = None
    entrypoint: Optional[str] = None
    defaults: Dict[str, Any] = Field(default_factory=dict)
