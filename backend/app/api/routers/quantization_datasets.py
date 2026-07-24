import mimetypes
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse

from app.api.routers import (
    build_success_response,
    get_quantization_dataset_service,
    get_request_context,
    raise_api_error_for_domain_error,
)
from app.api.schemas.common import ResponseEnvelope
from app.api.schemas.quantization_dataset import (
    QuantizationDatasetCreateRequest,
    QuantizationDatasetItem,
    QuantizationDatasetListData,
    QuantizationDatasetUpdateRequest,
    QuantizationImageDeleteRequest,
    QuantizationImageListData,
    QuantizationImageUploadResult,
)
from app.application.services import QuantizationDatasetService
from app.domain.common.exceptions import DomainError


router = APIRouter(
    prefix="/quantization-datasets", tags=["quantization-datasets"]
)


@router.get("", response_model=ResponseEnvelope[QuantizationDatasetListData])
async def list_quantization_datasets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    name: Optional[str] = Query(default=None),
    service: QuantizationDatasetService = Depends(
        get_quantization_dataset_service
    ),
    request_context=Depends(get_request_context),
):
    result = service.list_datasets(page=page, page_size=page_size, name=name)
    return build_success_response(
        data=QuantizationDatasetListData.model_validate(result),
        request_context=request_context,
    )


@router.post("", response_model=ResponseEnvelope[QuantizationDatasetItem])
async def create_quantization_dataset(
    payload: QuantizationDatasetCreateRequest,
    service: QuantizationDatasetService = Depends(
        get_quantization_dataset_service
    ),
    request_context=Depends(get_request_context),
):
    try:
        result = service.create_dataset(
            name=payload.name, description=payload.description
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=QuantizationDatasetItem.model_validate(result),
        request_context=request_context,
    )


@router.get("/{dataset_id}", response_model=ResponseEnvelope[QuantizationDatasetItem])
async def get_quantization_dataset(
    dataset_id: int,
    service: QuantizationDatasetService = Depends(
        get_quantization_dataset_service
    ),
    request_context=Depends(get_request_context),
):
    try:
        result = service.get_dataset(dataset_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=QuantizationDatasetItem.model_validate(result),
        request_context=request_context,
    )


@router.put("/{dataset_id}", response_model=ResponseEnvelope[QuantizationDatasetItem])
async def update_quantization_dataset(
    dataset_id: int,
    payload: QuantizationDatasetUpdateRequest,
    service: QuantizationDatasetService = Depends(
        get_quantization_dataset_service
    ),
    request_context=Depends(get_request_context),
):
    try:
        result = service.update_dataset(
            dataset_id, name=payload.name, description=payload.description
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=QuantizationDatasetItem.model_validate(result),
        request_context=request_context,
    )


@router.delete("/{dataset_id}", response_model=ResponseEnvelope[bool])
async def delete_quantization_dataset(
    dataset_id: int,
    service: QuantizationDatasetService = Depends(
        get_quantization_dataset_service
    ),
    request_context=Depends(get_request_context),
):
    try:
        result = service.delete_dataset(dataset_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(data=result, request_context=request_context)


@router.get(
    "/{dataset_id}/images",
    response_model=ResponseEnvelope[QuantizationImageListData],
)
async def list_quantization_images(
    dataset_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=200),
    service: QuantizationDatasetService = Depends(
        get_quantization_dataset_service
    ),
    request_context=Depends(get_request_context),
):
    try:
        result = service.list_images(dataset_id, page=page, page_size=page_size)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=QuantizationImageListData.model_validate(result),
        request_context=request_context,
    )


@router.post(
    "/{dataset_id}/images",
    response_model=ResponseEnvelope[QuantizationImageUploadResult],
)
async def upload_quantization_image(
    dataset_id: int,
    request: Request,
    filename: str = Query(min_length=1),
    service: QuantizationDatasetService = Depends(
        get_quantization_dataset_service
    ),
    request_context=Depends(get_request_context),
):
    content = await request.body()
    try:
        result = service.upload_image(
            dataset_id, filename=filename, content=content
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=QuantizationImageUploadResult.model_validate(result),
        request_context=request_context,
    )


@router.delete(
    "/{dataset_id}/images",
    response_model=ResponseEnvelope[QuantizationDatasetItem],
)
async def delete_quantization_images(
    dataset_id: int,
    payload: QuantizationImageDeleteRequest,
    service: QuantizationDatasetService = Depends(
        get_quantization_dataset_service
    ),
    request_context=Depends(get_request_context),
):
    try:
        result = service.delete_images(dataset_id, payload.names)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=QuantizationDatasetItem.model_validate(result),
        request_context=request_context,
    )


@router.get("/{dataset_id}/images/content", response_class=FileResponse)
async def get_quantization_image_content(
    dataset_id: int,
    filename: str = Query(min_length=1),
    service: QuantizationDatasetService = Depends(
        get_quantization_dataset_service
    ),
):
    try:
        image_path = service.resolve_image(dataset_id, filename)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    media_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    return FileResponse(
        image_path,
        media_type=media_type,
        filename=image_path.name,
        content_disposition_type="inline",
    )


@router.get("/{dataset_id}/ref-img-list", response_class=FileResponse)
async def download_quantization_image_list(
    dataset_id: int,
    service: QuantizationDatasetService = Depends(
        get_quantization_dataset_service
    ),
):
    try:
        image_list_path = service.resolve_image_list(dataset_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return FileResponse(
        image_list_path,
        media_type="text/plain; charset=utf-8",
        filename="ref_img_list.txt",
    )
