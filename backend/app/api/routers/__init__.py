from typing import Any, Generator, Optional

from fastapi import APIRouter, Depends, FastAPI, Request

from app.api.deps.request_context import (
    RequestContext,
    get_request_context,
)
from app.api.errors.http import APIError
from app.api.schemas.common import ResponseEnvelope
from app.application.services import (
    ConversionCommandService,
    SchedulerService,
    TaskQueryService,
    TemplateService,
    TrainingCommandService,
)
from app.bootstrap.container import ApplicationContainer
from app.domain.common.exceptions import (
    ClearMLAdapterError,
    DomainError,
    TemplateNotFoundError,
)
from app.infrastructure.clearml import ClearMLAdapter
from app.infrastructure.repositories import TaskRepository


def install_routers(app: FastAPI, container: ApplicationContainer) -> None:
    from app.api.routers.conversion import router as conversion_router
    from app.api.routers.system import router as system_router
    from app.api.routers.training import router as training_router

    api_router = APIRouter()
    api_router.include_router(training_router)
    api_router.include_router(conversion_router)
    api_router.include_router(system_router)
    app.include_router(api_router)


def build_success_response(
    data: Any,
    request_context: RequestContext,
    warnings: Optional[list] = None,
) -> ResponseEnvelope:
    return ResponseEnvelope(
        data=data,
        request_id=request_context.request_id,
        warnings=warnings or [],
    )


def raise_api_error_for_domain_error(exc: DomainError) -> None:
    if isinstance(exc, TemplateNotFoundError):
        raise APIError(status_code=404, code="TEMPLATE_NOT_FOUND", message=str(exc))
    if isinstance(exc, ClearMLAdapterError):
        raise APIError(status_code=502, code="CLEARML_ADAPTER_ERROR", message=str(exc))
    raise APIError(status_code=400, code="DOMAIN_ERROR", message=str(exc))


async def get_container(request: Request) -> ApplicationContainer:
    return request.app.state.container


async def get_task_repository(
    services: ApplicationContainer = Depends(get_container),
) -> Generator[TaskRepository, None, None]:
    session = services.session_factory()
    try:
        yield TaskRepository(session)
    finally:
        session.close()


async def get_task_query_service(
    repository: TaskRepository = Depends(get_task_repository),
) -> TaskQueryService:
    return TaskQueryService(task_repository=repository)


async def get_training_command_service(
    repository: TaskRepository = Depends(get_task_repository),
    services: ApplicationContainer = Depends(get_container),
) -> TrainingCommandService:
    return TrainingCommandService(
        template_service=services.training_template_service,
        clearml_adapter=services.clearml_adapter,
        task_repository=repository,
    )


async def get_conversion_command_service(
    repository: TaskRepository = Depends(get_task_repository),
    services: ApplicationContainer = Depends(get_container),
) -> ConversionCommandService:
    return ConversionCommandService(
        template_service=services.conversion_template_service,
        clearml_adapter=services.clearml_adapter,
        task_repository=repository,
    )


async def get_template_service(
    services: ApplicationContainer = Depends(get_container),
) -> TemplateService:
    return services.training_template_service


async def get_clearml_adapter(
    services: ApplicationContainer = Depends(get_container),
) -> ClearMLAdapter:
    return services.clearml_adapter


async def get_scheduler_service(
    services: ApplicationContainer = Depends(get_container),
) -> SchedulerService:
    return SchedulerService(scheduler_manager=services.scheduler_manager)


__all__ = [
    "build_success_response",
    "get_clearml_adapter",
    "get_conversion_command_service",
    "get_request_context",
    "get_scheduler_service",
    "get_task_query_service",
    "get_template_service",
    "get_training_command_service",
    "install_routers",
    "raise_api_error_for_domain_error",
]
