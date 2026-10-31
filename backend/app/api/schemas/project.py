from typing import List, Optional

from pydantic import BaseModel, Field

from app.domain.common.packaging import ProjectPackagingConfig


class ProjectItem(BaseModel):
    id: int
    project: str
    name: str
    model_type: Optional[str] = None
    model_architecture: Optional[str] = None
    description: Optional[str] = None
    exp_root_path: Optional[str] = None
    packaging: ProjectPackagingConfig = Field(default_factory=ProjectPackagingConfig)
    dataset_ids: List[int]
    epochs: Optional[int] = None
    batch: Optional[int] = None
    imgsz: Optional[int] = None
    created_at: str
    updated_at: str


class ProjectListData(BaseModel):
    items: List[ProjectItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class ProjectCreateRequest(BaseModel):
    project: str
    name: str
    model_type: str
    model_architecture: str
    description: Optional[str] = None
    exp_root_path: str
    packaging: ProjectPackagingConfig = Field(default_factory=ProjectPackagingConfig)
    dataset_ids: List[int]
    epochs: Optional[int] = None
    batch: Optional[int] = None
    imgsz: Optional[int] = None


class ProjectUpdateRequest(ProjectCreateRequest):
    pass
