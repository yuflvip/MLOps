from typing import Optional, Literal
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.api.routers import get_container, get_request_context, build_success_response, raise_api_error_for_domain_error
from app.application.services.weight_package_service import WeightPackageService
from app.domain.common.exceptions import DomainError

router = APIRouter(prefix="/weight-packages", tags=["weight-packages"])


class PackageRequest(BaseModel):
    exp_id: int = Field(gt=0)
    source_file: str = Field(min_length=1)
    package_name: Optional[str] = Field(default=None, max_length=244)
    platform: Literal["x86", "3403", "692", "530", "3588"]
    runtime: Optional[Literal["3403svp", "3403nnn"]] = None


class BuildRequest(PackageRequest):
    overwrite: bool = False
    preview_token: str = Field(min_length=64, max_length=64)


class UploadRequest(BaseModel):
    overwrite: bool = False


async def get_service(container=Depends(get_container)):
    session = container.session_factory()
    root = Path(container.settings.model_packaging.storage_root)
    if not root.is_absolute():
        root = container.config_dir.parent / root
    try:
        yield WeightPackageService(session, container.settings.model_packaging, root)
    finally:
        session.close()


def invoke(action, request_context):
    try:
        return build_success_response(action(), request_context)
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)


@router.post("/preview")
def preview(payload: PackageRequest, service=Depends(get_service), context=Depends(get_request_context)):
    return invoke(lambda: service.preview(**payload.model_dump()), context)


@router.post("")
def create(payload: BuildRequest, service=Depends(get_service), context=Depends(get_request_context)):
    return invoke(lambda: service.create(**payload.model_dump()), context)


@router.get("")
def list_packages(page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=200),
                  keyword: Optional[str] = None, platform: Optional[str] = None, uploaded: Optional[bool] = None,
                  model_type: Optional[str] = None, project_id: Optional[int] = Query(default=None, ge=1),
                  upload_status: Optional[str] = None,
                  service=Depends(get_service), context=Depends(get_request_context)):
    return invoke(lambda: service.list(page, page_size, keyword, platform, uploaded, model_type, project_id, upload_status), context)


@router.get("/{id}/download")
def download(id: int, service=Depends(get_service)):
    try:
        path, name = service.download(id)
        return FileResponse(path, filename=name, media_type="application/gzip")
    except DomainError as exc:
        raise_api_error_for_domain_error(exc)


@router.post("/{id}/upload")
def upload(id: int, payload: UploadRequest, service=Depends(get_service), context=Depends(get_request_context)):
    return invoke(lambda: service.upload(id, payload.overwrite), context)
