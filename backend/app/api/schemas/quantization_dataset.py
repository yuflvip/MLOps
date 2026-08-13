from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class QuantizationDatasetItem(BaseModel):
    id: int
    name: str
    storage_path: str
    image_list_path: str
    image_count: int
    size_bytes: int
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class QuantizationDatasetListData(BaseModel):
    items: List[QuantizationDatasetItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class QuantizationDatasetCreateRequest(BaseModel):
    name: str
    directory_name: str
    description: Optional[str] = None


class QuantizationDatasetUpdateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class QuantizationImageItem(BaseModel):
    name: str
    size_bytes: int
    modified_at: datetime


class QuantizationImageListData(BaseModel):
    items: List[QuantizationImageItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class QuantizationImageDeleteRequest(BaseModel):
    names: List[str] = Field(min_length=1)


class QuantizationImageUploadResult(BaseModel):
    image: QuantizationImageItem
    dataset: QuantizationDatasetItem
