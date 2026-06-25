from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectItem(BaseModel):
    id: int
    project: str
    name: str
    description: Optional[str] = None
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
    description: Optional[str] = None
    dataset_ids: List[int]
    epochs: Optional[int] = None
    batch: Optional[int] = None
    imgsz: Optional[int] = None


class ProjectUpdateRequest(ProjectCreateRequest):
    pass
