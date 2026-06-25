from typing import List, Optional

from pydantic import BaseModel, Field


class DatasetItem(BaseModel):
    id: int
    name: str
    path: str
    task_type: Optional[str] = None
    class_names: List[str]
    description: Optional[str] = None
    created_at: str
    updated_at: str


class DatasetListData(BaseModel):
    items: List[DatasetItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class DatasetCreateRequest(BaseModel):
    name: str
    path: str
    task_type: Optional[str] = None
    class_names: List[str]
    description: Optional[str] = None


class DatasetUpdateRequest(DatasetCreateRequest):
    pass
