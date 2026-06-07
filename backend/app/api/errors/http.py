import logging
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.schemas.common import ErrorEnvelope

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def _request_id_from_state(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
    request_id = _request_id_from_state(request)
    payload = ErrorEnvelope(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=request_id,
    )
    response = JSONResponse(status_code=exc.status_code, content=payload.model_dump())
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    request_id = _request_id_from_state(request)
    logger.error(
        "Unhandled exception during request processing",
        extra={"request_id": request_id},
        exc_info=True,
    )
    payload = ErrorEnvelope(
        code="INTERNAL_SERVER_ERROR",
        message="internal server error",
        request_id=request_id,
    )
    response = JSONResponse(status_code=500, content=payload.model_dump())
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def install_http_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(APIError, handle_api_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
