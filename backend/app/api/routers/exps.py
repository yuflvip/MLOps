from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.api.routers import (
    build_success_response,
    get_exp_service,
    get_request_context,
    raise_api_error_for_domain_error,
)
from app.api.schemas.common import ResponseEnvelope
from app.api.schemas.exp import (
    ExpApproveRequest,
    ExpArtifactListData,
    ExpArtifactPreviewData,
    ExpCandidateListData,
    ExpImportRequest,
    ExpItem,
    ExpListData,
    ExpRejectRequest,
)
from app.application.services import ExpService
from app.domain.common.exceptions import DomainError


router = APIRouter(tags=["exps"])


@router.get("/exps", response_model=ResponseEnvelope[ExpListData])
async def list_exps(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    project_id: Optional[int] = Query(default=None, ge=1),
    review_status: Optional[str] = Query(default=None),
    model_type: Optional[str] = Query(default=None),
    service: ExpService = Depends(get_exp_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.list_exps(
            page=page,
            page_size=page_size,
            project_id=project_id,
            review_status=review_status,
            model_type=model_type,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ExpListData(
            items=[ExpItem.model_validate(item) for item in result["items"]],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
        ),
        request_context=request_context,
    )


@router.get("/exps/{exp_id}", response_model=ResponseEnvelope[ExpItem])
async def get_exp(
    exp_id: int,
    service: ExpService = Depends(get_exp_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.get_exp(exp_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ExpItem.model_validate(result),
        request_context=request_context,
    )


@router.get(
    "/exps/{exp_id}/artifacts",
    response_model=ResponseEnvelope[ExpArtifactListData],
)
async def list_exp_artifacts(
    exp_id: int,
    service: ExpService = Depends(get_exp_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.list_artifacts(exp_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ExpArtifactListData.model_validate(result),
        request_context=request_context,
    )


@router.get(
    "/exps/{exp_id}/artifacts/preview",
    response_model=ResponseEnvelope[ExpArtifactPreviewData],
)
async def preview_exp_artifact(
    exp_id: int,
    path: str = Query(min_length=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
    sheet_name: Optional[str] = Query(default=None),
    service: ExpService = Depends(get_exp_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.preview_artifact(
            exp_id,
            relative_path=path,
            page=page,
            page_size=page_size,
            sheet_name=sheet_name,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ExpArtifactPreviewData.model_validate(result),
        request_context=request_context,
    )


@router.get("/exps/{exp_id}/artifacts/content", response_class=FileResponse)
async def get_exp_artifact_content(
    exp_id: int,
    path: str = Query(min_length=1),
    service: ExpService = Depends(get_exp_service),
):
    try:
        resolved, _relative_path = service.resolve_artifact(exp_id, path)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return FileResponse(resolved)


@router.get(
    "/projects/{project_id}/exp-candidates",
    response_model=ResponseEnvelope[ExpCandidateListData],
)
async def scan_exp_candidates(
    project_id: int,
    service: ExpService = Depends(get_exp_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.scan_candidates(project_id)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ExpCandidateListData.model_validate(result),
        request_context=request_context,
    )


@router.post(
    "/projects/{project_id}/exps/import",
    response_model=ResponseEnvelope[list[ExpItem]],
)
async def import_exps(
    project_id: int,
    payload: ExpImportRequest,
    service: ExpService = Depends(get_exp_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.import_exps(project_id, payload.relative_paths)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=[ExpItem.model_validate(item) for item in result],
        request_context=request_context,
    )


@router.post("/exps/{exp_id}/approve", response_model=ResponseEnvelope[ExpItem])
async def approve_exp(
    exp_id: int,
    payload: ExpApproveRequest,
    service: ExpService = Depends(get_exp_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.approve_exp(
            exp_id,
            version=payload.version,
            description=payload.description,
        )
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ExpItem.model_validate(result),
        request_context=request_context,
    )


@router.post("/exps/{exp_id}/reject", response_model=ResponseEnvelope[ExpItem])
async def reject_exp(
    exp_id: int,
    payload: ExpRejectRequest,
    service: ExpService = Depends(get_exp_service),
    request_context=Depends(get_request_context),
):
    try:
        result = service.reject_exp(exp_id, review_comment=payload.review_comment)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)
    return build_success_response(
        data=ExpItem.model_validate(result),
        request_context=request_context,
    )
