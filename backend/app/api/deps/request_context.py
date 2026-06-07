from dataclasses import dataclass
from typing import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.responses import Response


@dataclass(frozen=True)
class RequestContext:
    request_id: str


async def get_request_context(request: Request) -> RequestContext:
    request_id = getattr(request.state, "request_id", "")
    return RequestContext(request_id=request_id)


def install_request_context_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
