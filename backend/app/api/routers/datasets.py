from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.routers import (
    build_success_response,
    get_dataset_service,
    get_request_context,
    raise_api_error_for_domain_error,
)
from app.api.schemas.common import ResponseEnvelope
from app.api.schemas.dataset import (
    DatasetCreateRequest,
    DatasetItem,
    DatasetListData,
    DatasetUpdateRequest,
)
from app.application.services import DatasetService
from app.domain.common.exceptions import DomainError


router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get(
    "",
    response_model=ResponseEnvelope[DatasetListData],
    summary="List Datasets",
    description="返回数据集列表，供数据集管理页面展示。",
)
async def list_datasets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    name: Optional[str] = Query(default=None),
    path: Optional[str] = Query(default=None),
    task_type: Optional[str] = Query(default=None),
    service: DatasetService = Depends(get_dataset_service),
    request_context=Depends(get_request_context),
):
    result = service.list_datasets(
        page=page,
        page_size=page_size,
        name=name,
        path=path,
        task_type=task_type,
    )
    data = DatasetListData(
        items=[DatasetItem.model_validate(item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
    return build_success_response(data=data, request_context=request_context)


@router.get(
    "/{dataset_id}",
    response_model=ResponseEnvelope[DatasetItem],
    summary="Get Dataset Detail",
    description="根据数据集 ID 返回单条数据集详情。",
)
async def get_dataset(
    dataset_id: int,
    service: DatasetService = Depends(get_dataset_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.get_dataset(dataset_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=DatasetItem.model_validate(result),
        request_context=request_context,
    )


@router.post(
    "",
    response_model=ResponseEnvelope[DatasetItem],
    summary="Create Dataset",
    description="创建数据集。要求名称唯一、路径唯一且必须为本地绝对路径。",
)
async def create_dataset(
    payload: DatasetCreateRequest,
    service: DatasetService = Depends(get_dataset_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.create_dataset(
            name=payload.name,
            path=payload.path,
            task_type=payload.task_type,
            class_names=payload.class_names,
            description=payload.description,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=DatasetItem.model_validate(result),
        request_context=request_context,
    )


@router.put(
    "/{dataset_id}",
    response_model=ResponseEnvelope[DatasetItem],
    summary="Update Dataset",
    description="修改已有数据集。名称和路径仍需保持唯一。",
)
async def update_dataset(
    dataset_id: int,
    payload: DatasetUpdateRequest,
    service: DatasetService = Depends(get_dataset_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.update_dataset(
            dataset_id,
            name=payload.name,
            path=payload.path,
            task_type=payload.task_type,
            class_names=payload.class_names,
            description=payload.description,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=DatasetItem.model_validate(result),
        request_context=request_context,
    )


@router.delete(
    "/{dataset_id}",
    response_model=ResponseEnvelope[bool],
    summary="Delete Dataset",
    description="物理删除数据集记录。",
)
async def delete_dataset(
    dataset_id: int,
    service: DatasetService = Depends(get_dataset_service),
    request_context=Depends(get_request_context),
):
    try:
        deleted = service.delete_dataset(dataset_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=deleted,
        request_context=request_context,
    )
