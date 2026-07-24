from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelConversionCreateRequest(BaseModel):
    converter_code: str
    source_file: str
    output_file: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ModelConversionItem(BaseModel):
    id: int
    exp_id: int
    parent_conversion_id: Optional[int] = None
    converter_code: str
    source_file: str
    source_format: str
    target_platform: str
    target_format: str
    output_file: str
    status: str
    params: Dict[str, Any] = Field(default_factory=dict)
    result_files: List[str] = Field(default_factory=list)
    log_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ModelConversionListData(BaseModel):
    items: List[ModelConversionItem] = Field(default_factory=list)
    total: int = 0
