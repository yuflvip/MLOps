from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ExpItem(BaseModel):
    id: int
    project_id: int
    name: str
    relative_path: str
    resolved_path: str
    review_status: str
    version: Optional[str] = None
    description: Optional[str] = None
    review_comment: Optional[str] = None
    training_started_at: Optional[str] = None
    training_finished_at: Optional[str] = None
    validation_metric_value: Optional[float] = None
    imported_at: str
    reviewed_at: Optional[str] = None
    created_at: str
    updated_at: str


class ExpListData(BaseModel):
    items: List[ExpItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class ExpCandidate(BaseModel):
    name: str
    relative_path: str
    modified_at: str
    already_imported: bool


class ExpCandidateListData(BaseModel):
    project_id: int
    exp_root_path: str
    items: List[ExpCandidate] = Field(default_factory=list)


class ExpImportRequest(BaseModel):
    relative_paths: List[str]


class ExpApproveRequest(BaseModel):
    version: str
    description: Optional[str] = None


class ExpRejectRequest(BaseModel):
    review_comment: str


class ExpArtifactItem(BaseModel):
    name: str
    relative_path: str
    extension: str
    media_type: str
    size_bytes: int
    modified_at: str
    preview_kind: str


class ExpArtifactListData(BaseModel):
    items: List[ExpArtifactItem] = Field(default_factory=list)
    total: int = 0


class ExpArtifactPreviewData(BaseModel):
    relative_path: str
    preview_kind: str
    content: Optional[str] = None
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    sheet_names: List[str] = Field(default_factory=list)
    sheet_name: Optional[str] = None
    page: int = 1
    page_size: int = 100
    has_more: bool = False
    truncated: bool = False
