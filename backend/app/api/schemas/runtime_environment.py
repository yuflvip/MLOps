from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RuntimeEnvironmentItem(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    env_type: str
    python_path: Optional[str] = None
    working_dir: Optional[str] = None
    docker_image: Optional[str] = None
    extra_env: Dict[str, str] = Field(default_factory=dict)
    is_active: bool
    created_at: str
    updated_at: str


class RuntimeEnvironmentListData(BaseModel):
    items: List[RuntimeEnvironmentItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class RuntimeEnvironmentCreateRequest(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    env_type: str
    python_path: Optional[str] = None
    working_dir: Optional[str] = None
    docker_image: Optional[str] = None
    extra_env: Dict[str, str] = Field(default_factory=dict)
    is_active: bool = True


class RuntimeEnvironmentUpdateRequest(RuntimeEnvironmentCreateRequest):
    pass
