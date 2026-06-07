from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.api.schemas.training import TrainingSubmission, TrainingTaskSummary


class ConversionCreateRequest(BaseModel):
    parent_task_id: int
    task_name: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)


class ConversionCreateResult(BaseModel):
    task: TrainingTaskSummary
    submission: TrainingSubmission
