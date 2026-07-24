from fastapi import APIRouter, Depends

from app.api.routers import (
    build_success_response,
    get_model_conversion_service,
    get_request_context,
    raise_api_error_for_domain_error,
)
from app.api.schemas.common import ResponseEnvelope
from app.api.schemas.model_conversion import (
    ModelConversionCreateRequest,
    ModelConversionItem,
    ModelConversionListData,
)
from app.application.services import ModelConversionService
from app.domain.common.exceptions import DomainError


router = APIRouter(tags=["model-conversions"])


@router.post(
    "/exps/{exp_id}/conversions",
    response_model=ResponseEnvelope[ModelConversionItem],
)
async def create_model_conversion(
    exp_id: int,
    payload: ModelConversionCreateRequest,
    service: ModelConversionService = Depends(get_model_conversion_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.create_conversion(
            exp_id,
            converter_code=payload.converter_code,
            source_file=payload.source_file,
            output_file=payload.output_file,
            params=payload.params,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ModelConversionItem.model_validate(result),
        request_context=request_context,
    )


@router.get(
    "/exps/{exp_id}/conversions",
    response_model=ResponseEnvelope[ModelConversionListData],
)
async def list_model_conversions(
    exp_id: int,
    service: ModelConversionService = Depends(get_model_conversion_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.list_conversions(exp_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ModelConversionListData.model_validate(result),
        request_context=request_context,
    )


@router.get(
    "/conversions/{conversion_id}",
    response_model=ResponseEnvelope[ModelConversionItem],
)
async def get_model_conversion(
    conversion_id: int,
    service: ModelConversionService = Depends(get_model_conversion_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.get_conversion(conversion_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ModelConversionItem.model_validate(result),
        request_context=request_context,
    )
