from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.errors.http import APIError, TRAINING_TASK_NOT_FOUND_CODE
from app.api.routers import (
    build_success_response,
    get_clearml_adapter,
    get_request_context,
    get_task_query_service,
    get_template_service,
    get_training_command_service,
    raise_api_error_for_domain_error,
)
from app.api.schemas.common import ResponseEnvelope
from app.api.schemas.training import (
    TrainingCreateMetaData,
    TrainingCreateRequest,
    TrainingCreateResult,
    TrainingDetail,
    TrainingListData,
    TrainingQueueStatusItem,
    TrainingTemplateItem,
)
from app.application.services import (
    TaskQueryService,
    TemplateService,
    TrainingCommandService,
)
from app.domain.common.exceptions import DomainError
from app.infrastructure.clearml import ClearMLAdapter


router = APIRouter(prefix="/training", tags=["training"])


@router.get("", response_model=ResponseEnvelope[TrainingListData])
async def list_training_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    status: Optional[str] = Query(default=None),
    service: TaskQueryService = Depends(get_task_query_service),
    request_context=Depends(get_request_context),
):
    result = service.list_tasks(
        page=page,
        page_size=page_size,
        task_group="training",
        task_type="training",
        status=status,
    )
    data = TrainingListData.model_validate(result)
    return build_success_response(data=data, request_context=request_context)


@router.get("/create-meta", response_model=ResponseEnvelope[TrainingCreateMetaData])
async def get_training_create_meta(
    template_service: TemplateService = Depends(get_template_service),
    clearml_adapter: ClearMLAdapter = Depends(get_clearml_adapter),
    request_context=Depends(get_request_context),
):
    templates = [
        TrainingTemplateItem.model_validate(item)
        for item in template_service.list_templates()
    ]
    queues = [
        TrainingQueueStatusItem.model_validate(item)
        for item in clearml_adapter.list_queue_statuses()
    ]
    data = TrainingCreateMetaData(
        templates=templates,
        queues=queues,
    )
    return build_success_response(data=data, request_context=request_context)


@router.get("/{task_id}", response_model=ResponseEnvelope[TrainingDetail])
async def get_training_task_detail(
    task_id: int,
    service: TaskQueryService = Depends(get_task_query_service),
    request_context=Depends(get_request_context),
):
    result = service.get_task_detail(task_id)
    if result is None or result.get("task_group") != "training":
        raise APIError(
            status_code=404,
            code=TRAINING_TASK_NOT_FOUND_CODE,
            message="Training task '%s' was not found" % task_id,
        )
    data = TrainingDetail.model_validate(result)
    return build_success_response(data=data, request_context=request_context)


@router.post("", response_model=ResponseEnvelope[TrainingCreateResult])
async def create_training_task(
    payload: TrainingCreateRequest,
    service: TrainingCommandService = Depends(get_training_command_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.create_task(
            task_name=payload.task_name,
            template_name=payload.template_name,
            params=payload.params,
            queue_name=payload.queue_name,
            custom_data=payload.custom_data,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)

    data = TrainingCreateResult.model_validate(result)
    return build_success_response(
        data=data,
        request_context=request_context,
        warnings=result.get("warnings", []),
    )
