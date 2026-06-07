from fastapi import APIRouter, Depends, Request

from app.api.routers import (
    build_success_response,
    get_request_context,
    get_scheduler_service,
)
from app.api.schemas.common import ResponseEnvelope
from app.api.schemas.system import HealthData, RuntimeData
from app.application.services import SchedulerService


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=ResponseEnvelope[HealthData])
async def get_system_health(
    request: Request, request_context=Depends(get_request_context)
):
    data = HealthData(
        status="ok",
        app_name=request.app.state.container.settings.app.name,
    )
    return build_success_response(data=data, request_context=request_context)


@router.get("/runtime", response_model=ResponseEnvelope[RuntimeData])
async def get_system_runtime(
    request_context=Depends(get_request_context),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
):
    data = RuntimeData.model_validate(scheduler_service.get_runtime_status())
    return build_success_response(data=data, request_context=request_context)
