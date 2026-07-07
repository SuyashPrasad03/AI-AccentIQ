"""
Tests for GET /health endpoint.

Phase 1 acceptance criteria:
- Returns {status: "ok", mysql: "connected", mongo: "connected"} when both DBs are up.
- Returns {status: "degraded", mysql: "disconnected", ...} when MySQL is down — no 500.
- Returns {status: "degraded", ..., mongo: "disconnected"} when Mongo is down — no 500.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_all_connected(client):
    """Both databases healthy → status ok."""
    with (
        patch("app.modules.health.router._check_mysql", new=AsyncMock(return_value="connected")),
        patch("app.modules.health.router._check_mongo", new=AsyncMock(return_value="connected")),
    ):
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mysql"] == "connected"
    assert body["mongo"] == "connected"


@pytest.mark.asyncio
async def test_health_mysql_down(client):
    """MySQL disconnected → degraded, NOT a 500."""
    with (
        patch("app.modules.health.router._check_mysql", new=AsyncMock(return_value="disconnected")),
        patch("app.modules.health.router._check_mongo", new=AsyncMock(return_value="connected")),
    ):
        response = await client.get("/health")

    assert response.status_code == 200  # graceful — never a 500
    body = response.json()
    assert body["status"] == "degraded"
    assert body["mysql"] == "disconnected"
    assert body["mongo"] == "connected"


@pytest.mark.asyncio
async def test_health_mongo_down(client):
    """MongoDB disconnected → degraded, NOT a 500."""
    with (
        patch("app.modules.health.router._check_mysql", new=AsyncMock(return_value="connected")),
        patch("app.modules.health.router._check_mongo", new=AsyncMock(return_value="disconnected")),
    ):
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["mysql"] == "connected"
    assert body["mongo"] == "disconnected"


@pytest.mark.asyncio
async def test_health_response_shape(client):
    """Response always has the required keys regardless of DB state."""
    with (
        patch("app.modules.health.router._check_mysql", new=AsyncMock(return_value="connected")),
        patch("app.modules.health.router._check_mongo", new=AsyncMock(return_value="connected")),
    ):
        response = await client.get("/health")

    body = response.json()
    assert set(body.keys()) == {"status", "mysql", "mongo"}
