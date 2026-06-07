from fastapi import APIRouter, Depends

from app.api.routers import (
    build_success_response,
    get_conversion_command_service,
    get_request_context,
    raise_api_error_for_domain_error,
)
from app.api.schemas.common import ResponseEnvelope
from app.api.schemas.conversion import (
    ConversionCreateRequest,
    ConversionCreateResult,
)
from app.application.services import ConversionCommandService
from app.domain.common.exceptions import DomainError


router = APIRouter(prefix="/conversion", tags=["conversion"])


@router.post("/onnx", response_model=ResponseEnvelope[ConversionCreateResult])
async def create_onnx_conversion_task(
    payload: ConversionCreateRequest,
    service: ConversionCommandService = Depends(get_conversion_command_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.create_export_onnx_task(
            parent_task_id=payload.parent_task_id,
            task_name=payload.task_name,
            params=payload.params,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)

    data = ConversionCreateResult.model_validate(result)
    return build_success_response(
        data=data,
        request_context=request_context,
        warnings=result.get("warnings", []),
    )
