from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.routers import (
    build_success_response,
    get_request_context,
    get_runtime_environment_service,
    raise_api_error_for_domain_error,
)
from app.api.schemas.common import ResponseEnvelope
from app.api.schemas.runtime_environment import (
    RuntimeEnvironmentCreateRequest,
    RuntimeEnvironmentItem,
    RuntimeEnvironmentListData,
    RuntimeEnvironmentUpdateRequest,
)
from app.application.services import RuntimeEnvironmentService
from app.domain.common.exceptions import DomainError


router = APIRouter(prefix="/runtime-environments", tags=["runtime-environments"])


@router.get(
    "",
    response_model=ResponseEnvelope[RuntimeEnvironmentListData],
    summary="List Runtime Environments",
    description="返回运行环境列表，支持分页和按 code/name/env_type/status 查询。",
)
async def list_runtime_environments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    code: Optional[str] = Query(default=None),
    name: Optional[str] = Query(default=None),
    env_type: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    service: RuntimeEnvironmentService = Depends(get_runtime_environment_service),
    request_context=Depends(get_request_context),
):
    result = service.list_runtime_environments(
        page=page,
        page_size=page_size,
        code=code,
        name=name,
        env_type=env_type,
        is_active=is_active,
    )
    data = RuntimeEnvironmentListData(
        items=[RuntimeEnvironmentItem.model_validate(item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
    return build_success_response(data=data, request_context=request_context)


@router.get(
    "/{runtime_environment_id}",
    response_model=ResponseEnvelope[RuntimeEnvironmentItem],
    summary="Get Runtime Environment Detail",
    description="根据运行环境 ID 返回单条详情。",
)
async def get_runtime_environment(
    runtime_environment_id: int,
    service: RuntimeEnvironmentService = Depends(get_runtime_environment_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.get_runtime_environment(runtime_environment_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=RuntimeEnvironmentItem.model_validate(result),
        request_context=request_context,
    )


@router.post(
    "",
    response_model=ResponseEnvelope[RuntimeEnvironmentItem],
    summary="Create Runtime Environment",
    description="创建运行环境。要求 code 唯一，并校验 env_type 对应字段。",
)
async def create_runtime_environment(
    payload: RuntimeEnvironmentCreateRequest,
    service: RuntimeEnvironmentService = Depends(get_runtime_environment_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.create_runtime_environment(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            env_type=payload.env_type,
            python_path=payload.python_path,
            working_dir=payload.working_dir,
            docker_image=payload.docker_image,
            extra_env=payload.extra_env,
            is_active=payload.is_active,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=RuntimeEnvironmentItem.model_validate(result),
        request_context=request_context,
    )


@router.put(
    "/{runtime_environment_id}",
    response_model=ResponseEnvelope[RuntimeEnvironmentItem],
    summary="Update Runtime Environment",
    description="更新运行环境。",
)
async def update_runtime_environment(
    runtime_environment_id: int,
    payload: RuntimeEnvironmentUpdateRequest,
    service: RuntimeEnvironmentService = Depends(get_runtime_environment_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.update_runtime_environment(
            runtime_environment_id,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            env_type=payload.env_type,
            python_path=payload.python_path,
            working_dir=payload.working_dir,
            docker_image=payload.docker_image,
            extra_env=payload.extra_env,
            is_active=payload.is_active,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=RuntimeEnvironmentItem.model_validate(result),
        request_context=request_context,
    )


@router.delete(
    "/{runtime_environment_id}",
    response_model=ResponseEnvelope[bool],
    summary="Delete Runtime Environment",
    description="物理删除运行环境记录。",
)
async def delete_runtime_environment(
    runtime_environment_id: int,
    service: RuntimeEnvironmentService = Depends(get_runtime_environment_service),
    request_context=Depends(get_request_context),
):
    try:
        deleted = service.delete_runtime_environment(runtime_environment_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(data=deleted, request_context=request_context)
