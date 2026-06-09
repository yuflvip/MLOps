from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TrainingTaskSummary(BaseModel):
    id: int
    parent_task_id: Optional[int] = None
    task_name: str
    task_group: str
    task_type: str
    task_source: Optional[str] = None
    status: str
    clearml_task_id: Optional[str] = None
    queue_name: Optional[str] = None
    template_name: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    parameter_snapshot: Optional[Dict[str, Any]] = None
    runtime_snapshot: Optional[Dict[str, Any]] = None
    custom_data: Optional[Dict[str, Any]] = None
    result_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    last_sync_status: Optional[str] = None
    last_sync_error: Optional[str] = None
    sync_version: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TrainingDetail(TrainingTaskSummary):
    pass


class TrainingListData(BaseModel):
    items: List[TrainingTaskSummary] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class TrainingTemplateItem(BaseModel):
    class RuntimeArtifactItem(BaseModel):
        name: str
        role: str
        format: str
        path: str

    class RuntimeConfigItem(BaseModel):
        launcher: Optional[str] = None
        script_path: Optional[str] = None
        working_dir: Optional[str] = None
        env: Dict[str, Any] = Field(default_factory=dict)
        artifacts: List["TrainingTemplateItem.RuntimeArtifactItem"] = Field(
            default_factory=list
        )

    name: str
    display_name: Optional[str] = None
    queue: Optional[str] = None
    entrypoint: Optional[str] = None
    defaults: Dict[str, Any] = Field(default_factory=dict)
    runtime: Optional[RuntimeConfigItem] = None
    execution_defaults: Dict[str, Any] = Field(default_factory=dict)


class TrainingQueueAgentItem(BaseModel):
    name: str
    status: Optional[str] = None


class TrainingQueueStatusItem(BaseModel):
    queue_name: str
    agent_count: int
    has_online_agents: bool
    agents: List[TrainingQueueAgentItem] = Field(default_factory=list)
    last_seen: Optional[str] = None


class TrainingCreateMetaData(BaseModel):
    templates: List[TrainingTemplateItem] = Field(default_factory=list)
    queues: List[TrainingQueueStatusItem] = Field(default_factory=list)


class TrainingCreateRequest(BaseModel):
    task_name: str
    template_name: str
    params: Dict[str, Any] = Field(default_factory=dict)
    execution_params: Dict[str, Any] = Field(default_factory=dict)
    queue_name: Optional[str] = None
    custom_data: Dict[str, Any] = Field(default_factory=dict)


class TrainingSubmission(BaseModel):
    clearml_task_id: Optional[str] = None
    status: Optional[str] = None


class TrainingCreateResult(BaseModel):
    task: TrainingTaskSummary
    submission: TrainingSubmission
