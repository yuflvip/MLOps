from pathlib import Path
from typing import Any, Generator, Optional

from fastapi import APIRouter, Depends, FastAPI, Request

from app.api.deps.request_context import (
    RequestContext,
    get_request_context,
)
from app.api.errors.http import (
    APIError,
    CLEARML_ADAPTER_ERROR_CODE,
    DATASET_CONFLICT_CODE,
    DATASET_NOT_FOUND_CODE,
    DOMAIN_ERROR_CODE,
    EXP_CONFLICT_CODE,
    EXP_NOT_FOUND_CODE,
    PROJECT_CONFLICT_CODE,
    PROJECT_NOT_FOUND_CODE,
    QUANTIZATION_DATASET_CONFLICT_CODE,
    QUANTIZATION_DATASET_NOT_FOUND_CODE,
    RUNTIME_ENVIRONMENT_CONFLICT_CODE,
    RUNTIME_ENVIRONMENT_NOT_FOUND_CODE,
    TEMPLATE_NOT_FOUND_CODE,
)
from app.api.schemas.common import ResponseEnvelope
from app.application.services import (
    ConversionCommandService,
    DatasetService,
    QuantizationDatasetService,
    ExpService,
    ModelConversionService,
    ProjectService,
    RuntimeEnvironmentService,
    SchedulerService,
    TaskQueryService,
    TemplateService,
    TrainingCommandService,
)
from app.bootstrap.container import ApplicationContainer
from app.domain.common.exceptions import (
    ClearMLAdapterError,
    DatasetConflictError,
    DatasetNotFoundError,
    DomainError,
    ExpConflictError,
    ExpNotFoundError,
    ProjectConflictError,
    ProjectNotFoundError,
    QuantizationDatasetConflictError,
    QuantizationDatasetNotFoundError,
    RuntimeEnvironmentConflictError,
    RuntimeEnvironmentNotFoundError,
    TemplateNotFoundError,
)
from app.infrastructure.clearml import ClearMLAdapter
from app.infrastructure.repositories import (
    DatasetRepository,
    ExpRepository,
    ModelConversionRepository,
    ProjectRepository,
    QuantizationDatasetRepository,
    RuntimeEnvironmentRepository,
    TaskRepository,
)


def install_routers(app: FastAPI, container: ApplicationContainer) -> None:
    from app.api.routers.clearml import router as clearml_router
    from app.api.routers.conversion import router as conversion_router
    from app.api.routers.datasets import router as dataset_router
    from app.api.routers.exps import router as exp_router
    from app.api.routers.model_conversions import router as model_conversion_router
    from app.api.routers.projects import router as project_router
    from app.api.routers.quantization_datasets import (
        router as quantization_dataset_router,
    )
    from app.api.routers.runtime_environments import router as runtime_environment_router
    from app.api.routers.system import router as system_router
    from app.api.routers.training import router as training_router

    api_router = APIRouter()
    api_router.include_router(dataset_router)
    api_router.include_router(exp_router)
    api_router.include_router(model_conversion_router)
    api_router.include_router(project_router)
    api_router.include_router(quantization_dataset_router)
    api_router.include_router(runtime_environment_router)
    api_router.include_router(training_router)
    api_router.include_router(conversion_router)
    api_router.include_router(system_router)
    api_router.include_router(clearml_router)

    api_prefix = container.settings.app.api_prefix
    app.include_router(api_router, prefix=api_prefix)


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
        raise APIError(status_code=404, code=TEMPLATE_NOT_FOUND_CODE, message=str(exc))
    if isinstance(exc, DatasetNotFoundError):
        raise APIError(status_code=404, code=DATASET_NOT_FOUND_CODE, message=str(exc))
    if isinstance(exc, DatasetConflictError):
        raise APIError(status_code=409, code=DATASET_CONFLICT_CODE, message=str(exc))
    if isinstance(exc, QuantizationDatasetNotFoundError):
        raise APIError(
            status_code=404,
            code=QUANTIZATION_DATASET_NOT_FOUND_CODE,
            message=str(exc),
        )
    if isinstance(exc, QuantizationDatasetConflictError):
        raise APIError(
            status_code=409,
            code=QUANTIZATION_DATASET_CONFLICT_CODE,
            message=str(exc),
        )
    if isinstance(exc, ProjectNotFoundError):
        raise APIError(status_code=404, code=PROJECT_NOT_FOUND_CODE, message=str(exc))
    if isinstance(exc, ProjectConflictError):
        raise APIError(status_code=409, code=PROJECT_CONFLICT_CODE, message=str(exc))
    if isinstance(exc, ExpNotFoundError):
        raise APIError(status_code=404, code=EXP_NOT_FOUND_CODE, message=str(exc))
    if isinstance(exc, ExpConflictError):
        raise APIError(status_code=409, code=EXP_CONFLICT_CODE, message=str(exc))
    if isinstance(exc, RuntimeEnvironmentNotFoundError):
        raise APIError(
            status_code=404,
            code=RUNTIME_ENVIRONMENT_NOT_FOUND_CODE,
            message=str(exc),
        )
    if isinstance(exc, RuntimeEnvironmentConflictError):
        raise APIError(
            status_code=409,
            code=RUNTIME_ENVIRONMENT_CONFLICT_CODE,
            message=str(exc),
        )
    if isinstance(exc, ClearMLAdapterError):
        raise APIError(status_code=502, code=CLEARML_ADAPTER_ERROR_CODE, message=str(exc))
    raise APIError(status_code=400, code=DOMAIN_ERROR_CODE, message=str(exc))


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


async def get_dataset_repository(
    services: ApplicationContainer = Depends(get_container),
) -> Generator[DatasetRepository, None, None]:
    session = services.session_factory()
    try:
        yield DatasetRepository(session)
    finally:
        session.close()


async def get_project_repository(
    services: ApplicationContainer = Depends(get_container),
) -> Generator[ProjectRepository, None, None]:
    session = services.session_factory()
    try:
        yield ProjectRepository(session)
    finally:
        session.close()


async def get_runtime_environment_repository(
    services: ApplicationContainer = Depends(get_container),
) -> Generator[RuntimeEnvironmentRepository, None, None]:
    session = services.session_factory()
    try:
        yield RuntimeEnvironmentRepository(session)
    finally:
        session.close()


async def get_task_query_service(
    repository: TaskRepository = Depends(get_task_repository),
) -> TaskQueryService:
    return TaskQueryService(task_repository=repository)


async def get_dataset_service(
    repository: DatasetRepository = Depends(get_dataset_repository),
) -> DatasetService:
    return DatasetService(dataset_repository=repository)


async def get_quantization_dataset_service(
    services: ApplicationContainer = Depends(get_container),
) -> Generator[QuantizationDatasetService, None, None]:
    session = services.session_factory()
    try:
        storage_root = Path(services.settings.quantization_dataset.storage_root)
        if not storage_root.is_absolute():
            storage_root = (services.config_dir.parent / storage_root).resolve()
        yield QuantizationDatasetService(
            QuantizationDatasetRepository(session),
            storage_root=storage_root,
            max_image_size_mb=(
                services.settings.quantization_dataset.max_image_size_mb
            ),
        )
    finally:
        session.close()


async def get_project_service(
    services: ApplicationContainer = Depends(get_container),
) -> Generator[ProjectService, None, None]:
    # Project validation reads datasets before writing the project.  Both
    # repositories must use one transaction: two SQLite connections here can
    # make the read transaction block its own write commit.
    session = services.session_factory()
    try:
        yield ProjectService(
            project_repository=ProjectRepository(session),
            dataset_repository=DatasetRepository(session),
        )
    finally:
        session.close()


async def get_exp_service(
    services: ApplicationContainer = Depends(get_container),
) -> Generator[ExpService, None, None]:
    session = services.session_factory()
    try:
        yield ExpService(
            exp_repository=ExpRepository(session),
            project_repository=ProjectRepository(session),
        )
    finally:
        session.close()


async def get_model_conversion_service(
    services: ApplicationContainer = Depends(get_container),
) -> Generator[ModelConversionService, None, None]:
    session = services.session_factory()
    try:
        yield ModelConversionService(
            conversion_repository=ModelConversionRepository(session),
            exp_repository=ExpRepository(session),
            project_repository=ProjectRepository(session),
            settings=services.settings.model_conversion,
            scheduler=services.model_conversion_scheduler,
        )
    finally:
        session.close()


async def get_runtime_environment_service(
    repository: RuntimeEnvironmentRepository = Depends(get_runtime_environment_repository),
) -> RuntimeEnvironmentService:
    return RuntimeEnvironmentService(runtime_environment_repository=repository)


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
    "get_dataset_service",
    "get_exp_service",
    "get_model_conversion_service",
    "get_quantization_dataset_service",
    "get_project_service",
    "get_runtime_environment_service",
    "get_request_context",
    "get_scheduler_service",
    "get_task_query_service",
    "get_template_service",
    "get_training_command_service",
    "install_routers",
    "raise_api_error_for_domain_error",
]
