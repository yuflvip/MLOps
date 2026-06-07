import asyncio

import httpx
from app.api.schemas.common import ResponseEnvelope
from app.main import create_app


def test_response_envelope_defaults():
    response = ResponseEnvelope(data={"ok": True})

    assert response.code == "OK"
    assert response.message == "success"
    assert response.warnings == []


def test_unexpected_error_returns_envelope_and_request_id_header():
    app = create_app()

    @app.get("/_test/error")
    async def raise_error() -> None:
        raise RuntimeError("boom")

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/_test/error")

    response = asyncio.run(send_request())

    assert response.status_code == 500
    assert response.headers["X-Request-ID"]
    assert response.json() == {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "internal server error",
        "details": None,
        "request_id": response.headers["X-Request-ID"],
    }
