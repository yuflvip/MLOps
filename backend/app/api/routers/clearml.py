from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.api.routers import (
    build_success_response,
    get_clearml_adapter,
    get_request_context,
    raise_api_error_for_domain_error,
)
from app.api.schemas.common import ResponseEnvelope
from app.domain.common.exceptions import ClearMLAdapterError
from app.infrastructure.clearml import ClearMLAdapter


router = APIRouter(prefix="/clearml", tags=["clearml"])


@router.get("/events/get_task_log", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_task_log(
    task: str = Query(..., description="ClearML task ID"),
    batch_size: int = Query(500, ge=1, le=5000),
    from_timestamp: Optional[int] = Query(None, description="Pagination cursor (timestamp of last event)"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    request_context=Depends(get_request_context),
    clearml_adapter: ClearMLAdapter = Depends(get_clearml_adapter),
):
    """Proxy to ClearML events.get_task_log — returns task console log events."""
    try:
        data = clearml_adapter.get_task_log(
            task=task,
            batch_size=batch_size,
            from_timestamp=from_timestamp,
            order=order,
        )
    except ClearMLAdapterError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(data=data, request_context=request_context)
