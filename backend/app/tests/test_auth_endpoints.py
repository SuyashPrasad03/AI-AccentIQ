"""
Integration tests for auth and quota HTTP endpoints.
Uses the FastAPI test client with overridden DB dependencies (no real MySQL needed).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.mysql.base import get_db
from app.main import create_app
from app.modules.auth.models import User
from app.modules.auth.security import hash_password


# ── Test fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def app():
    application = create_app()
    return application


def _mock_db():
    """Build a minimal AsyncSession mock."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
async def client(app):
    """HTTP client with mocked MongoDB (no container needed)."""
    with patch("app.db.mongo.client.init_mongo", new=AsyncMock()):
        with patch("app.db.mongo.client.close_mongo", new=AsyncMock()):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                yield ac


# ── /auth/register ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_sends_otp(client, app) -> None:
    db = _mock_db()

    no_user_result = MagicMock()
    no_user_result.scalar_one_or_none = MagicMock(return_value=None)

    no_otps_result = MagicMock()
    no_otps_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

    db.execute = AsyncMock(side_effect=[no_user_result, no_otps_result])

    app.dependency_overrides[get_db] = lambda: db

    with patch("app.modules.auth.service.send_otp_email", new=AsyncMock()):
        response = await client.post("/auth/register", json={"email": "new@example.com"})

    assert response.status_code == 202
    body = response.json()
    assert body["email"] == "new@example.com"
    assert "Verification" in body["message"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_duplicate_verified_returns_409(client, app) -> None:
    db = _mock_db()
    existing = User(
        id="u1",
        email="taken@example.com",
        email_verified_at=datetime.now(UTC),
    )
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=existing)
    db.execute = AsyncMock(return_value=result)
    app.dependency_overrides[get_db] = lambda: db

    response = await client.post("/auth/register", json={"email": "taken@example.com"})
    assert response.status_code == 409
    assert response.json()["error_code"] == "CONFLICT"

    app.dependency_overrides.clear()


# ── /auth/login ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_with_wrong_password_returns_401(client, app) -> None:
    db = _mock_db()
    user = User(
        id="u1",
        email="u@example.com",
        password_hash=hash_password("correct"),
        email_verified_at=datetime.now(UTC),
    )
    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)
    db.execute = AsyncMock(return_value=user_result)
    app.dependency_overrides[get_db] = lambda: db

    response = await client.post(
        "/auth/login",
        json={"email": "u@example.com", "password": "wrong_password"},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTHENTICATION_FAILED"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_nonexistent_user_returns_401(client, app) -> None:
    db = _mock_db()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=result)
    app.dependency_overrides[get_db] = lambda: db

    response = await client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "irrelevant"},
    )
    assert response.status_code == 401

    app.dependency_overrides.clear()


# ── /auth/refresh ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client) -> None:
    response = await client.post("/auth/refresh")
    assert response.status_code == 401


# ── /auth/me ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_without_token_returns_401(client) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token(client, app) -> None:
    from app.modules.auth.security import create_access_token

    db = _mock_db()
    user = User(
        id="u-valid",
        email="valid@example.com",
        email_verified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=user)
    db.execute = AsyncMock(return_value=result)
    app.dependency_overrides[get_db] = lambda: db

    token = create_access_token("u-valid")
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "valid@example.com"

    app.dependency_overrides.clear()


# ── /quota/status ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quota_status_new_anon_visitor(client, app) -> None:
    db = _mock_db()
    # The quota router assigns a new anon session then calls get_quota_status.
    # get_quota_status does a SELECT which returns None (no row yet).
    no_row_result = MagicMock()
    no_row_result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=no_row_result)
    app.dependency_overrides[get_db] = lambda: db

    response = await client.get("/quota/status")
    assert response.status_code == 200
    body = response.json()
    assert body["used"] == 0
    assert body["requires_auth"] is False
    # New anon visitor should get a session cookie assigned
    assert "anon_session_id" in response.headers.get("set-cookie", "")

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_quota_increment_stub(client, app) -> None:
    # This endpoint touches real DB via ON DUPLICATE KEY — test just the happy
    # shape at the HTTP level with a fully mocked get_db.
    from app.modules.quota.models import AnonymousUsage
    from app.modules.auth.dependencies import Identity
    from app.modules.quota import service as quota_service

    db = _mock_db()
    usage = AnonymousUsage(anon_session_id="s1", analyses_used=0)
    # Mock both the INSERT result and the SELECT result
    insert_result = MagicMock()
    select_result = MagicMock()
    select_result.scalar_one = MagicMock(return_value=usage)
    db.execute = AsyncMock(side_effect=[insert_result, select_result])
    app.dependency_overrides[get_db] = lambda: db

    response = await client.post("/quota/increment")
    # New anon visitor gets a cookie set; status is 200 (incremented) or 402 (exceeded)
    assert response.status_code in (200, 402)

    app.dependency_overrides.clear()


# ── /consent ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_consent_audio_processing(client, app) -> None:
    from app.modules.compliance.models import ConsentEvent

    db = _mock_db()

    def capture_and_set(obj: object) -> None:
        if isinstance(obj, ConsentEvent):
            obj.id = "ce-1"
            obj.granted_at = datetime.now(UTC)

    db.add.side_effect = capture_and_set
    app.dependency_overrides[get_db] = lambda: db

    response = await client.post(
        "/consent",
        json={"consent_type": "audio_processing"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["consent_type"] == "audio_processing"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_record_consent_invalid_type_returns_422(client) -> None:
    response = await client.post(
        "/consent",
        json={"consent_type": "something_invalid"},
    )
    assert response.status_code == 422
