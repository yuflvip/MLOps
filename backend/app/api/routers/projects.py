from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.routers import (
    build_success_response,
    get_project_service,
    get_request_context,
    raise_api_error_for_domain_error,
)
from app.api.schemas.common import ResponseEnvelope
from app.api.schemas.project import (
    ProjectCreateRequest,
    ProjectItem,
    ProjectListData,
    ProjectUpdateRequest,
)
from app.application.services import ProjectService
from app.domain.common.exceptions import DomainError


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get(
    "",
    response_model=ResponseEnvelope[ProjectListData],
    summary="List Projects",
    description="返回项目列表，支持分页和按 project/name 查询。",
)
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    project: Optional[str] = Query(default=None),
    name: Optional[str] = Query(default=None),
    model_type: Optional[str] = Query(default=None),
    service: ProjectService = Depends(get_project_service),
    request_context=Depends(get_request_context),
):
    result = service.list_projects(
        page=page,
        page_size=page_size,
        project=project,
        name=name,
        model_type=model_type,
    )
    data = ProjectListData(
        items=[ProjectItem.model_validate(item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
    return build_success_response(data=data, request_context=request_context)


@router.get(
    "/{project_id}",
    response_model=ResponseEnvelope[ProjectItem],
    summary="Get Project Detail",
    description="根据项目 ID 返回单条项目详情。",
)
async def get_project(
    project_id: int,
    service: ProjectService = Depends(get_project_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.get_project(project_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ProjectItem.model_validate(result),
        request_context=request_context,
    )


@router.post(
    "",
    response_model=ResponseEnvelope[ProjectItem],
    summary="Create Project",
    description="创建项目。要求 project 唯一，dataset_ids 必须全部存在。",
)
async def create_project(
    payload: ProjectCreateRequest,
    service: ProjectService = Depends(get_project_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.create_project(
            project=payload.project,
            name=payload.name,
            model_type=payload.model_type,
            model_architecture=payload.model_architecture,
            description=payload.description,
            exp_root_path=payload.exp_root_path,
            dataset_ids=payload.dataset_ids,
            epochs=payload.epochs,
            batch=payload.batch,
            imgsz=payload.imgsz,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ProjectItem.model_validate(result),
        request_context=request_context,
    )


@router.put(
    "/{project_id}",
    response_model=ResponseEnvelope[ProjectItem],
    summary="Update Project",
    description="更新项目基础信息和绑定的数据集。",
)
async def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    service: ProjectService = Depends(get_project_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.update_project(
            project_id,
            project=payload.project,
            name=payload.name,
            model_type=payload.model_type,
            model_architecture=payload.model_architecture,
            description=payload.description,
            exp_root_path=payload.exp_root_path,
            dataset_ids=payload.dataset_ids,
            epochs=payload.epochs,
            batch=payload.batch,
            imgsz=payload.imgsz,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ProjectItem.model_validate(result),
        request_context=request_context,
    )


@router.delete(
    "/{project_id}",
    response_model=ResponseEnvelope[bool],
    summary="Delete Project",
    description="物理删除项目记录。",
)
async def delete_project(
    project_id: int,
    service: ProjectService = Depends(get_project_service),
    request_context=Depends(get_request_context),
):
    try:
        deleted = service.delete_project(project_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(data=deleted, request_context=request_context)
