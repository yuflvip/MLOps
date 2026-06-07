from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


DataT = TypeVar("DataT")


class ResponseEnvelope(BaseModel, Generic[DataT]):
    code: str = "OK"
    message: str = "success"
    data: Optional[DataT] = None
    request_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
    request_id: Optional[str] = None
