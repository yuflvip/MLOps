from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_system_runtime_route_returns_scheduler_status():
    app = create_app(config_path=BACKEND_ROOT / "config" / "app.yaml")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/mlops/system/runtime")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["message"] == "success"
    assert payload["warnings"] == []
    assert payload["data"]["scheduler"]["enabled"] is True
