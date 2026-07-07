"""
Auth + quota unit and integration tests.

These tests use only mocked DB sessions and in-process logic — no real MySQL needed.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError, ConflictError, ValidationError
from app.modules.auth import service as auth_service
from app.modules.auth.models import OtpCode, RefreshToken, User
from app.modules.auth.security import (
    create_access_token,
    decode_access_token,
    generate_otp,
    hash_otp,
    hash_password,
    hash_refresh_token,
    sign_anon_session_id,
    unsign_anon_session_id,
    verify_otp,
    verify_password,
)


# ── Security helpers ──────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_and_verify(self) -> None:
        plain = "SecurePass123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed)

    def test_wrong_password_fails(self) -> None:
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)


class TestJwtTokens:
    def test_access_token_roundtrip(self) -> None:
        token = create_access_token("user-123")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_expired_token_raises(self) -> None:
        import jwt as _jwt

        from app.core.settings import settings

        payload = {
            "sub": "user-123",
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        }
        token = _jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        with pytest.raises(_jwt.ExpiredSignatureError):
            decode_access_token(token)


class TestOtpHashing:
    def test_otp_generation_is_6_digits(self) -> None:
        for _ in range(10):
            otp = generate_otp()
            assert len(otp) == 6
            assert otp.isdigit()

    def test_otp_hash_verify(self) -> None:
        otp = "123456"
        hashed = hash_otp(otp)
        assert verify_otp(otp, hashed)
        assert not verify_otp("654321", hashed)


class TestAnonSessionSigning:
    def test_sign_and_verify(self) -> None:
        raw_id = "abc123deadbeef"
        signed = sign_anon_session_id(raw_id)
        assert "." in signed
        assert unsign_anon_session_id(signed) == raw_id

    def test_tampered_signature_returns_none(self) -> None:
        signed = sign_anon_session_id("original")
        tampered = signed[:-4] + "xxxx"
        assert unsign_anon_session_id(tampered) is None

    def test_missing_dot_returns_none(self) -> None:
        assert unsign_anon_session_id("nodotinhere") is None


# ── Auth service unit tests (mocked DB) ──────────────────────────────────────

def _make_db_session() -> AsyncMock:
    """Return a mock that behaves like an AsyncSession."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


class TestRegisterUser:
    @pytest.mark.asyncio
    async def test_duplicate_verified_email_raises_conflict(self) -> None:
        db = _make_db_session()
        existing = User(
            id="u1",
            email="test@example.com",
            email_verified_at=datetime.now(UTC),
        )
        # Mock the DB scalar result
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=existing)
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(ConflictError):
            await auth_service.register_user("test@example.com", db)

    @pytest.mark.asyncio
    async def test_rate_limit_raises_validation_error(self) -> None:
        from app.core.rate_limit import OtpRateLimiter

        limiter = OtpRateLimiter()
        with patch("app.modules.auth.service.otp_rate_limiter", limiter):
            # Exhaust the rate limit
            for _ in range(100):
                limiter.record("rl@example.com")

            db = _make_db_session()
            with pytest.raises(ValidationError) as exc_info:
                await auth_service.register_user("rl@example.com", db)
            assert "Too many" in exc_info.value.message


class TestVerifyOtp:
    @pytest.mark.asyncio
    async def test_wrong_otp_raises_validation_error(self) -> None:
        db = _make_db_session()
        otp_record = OtpCode(
            id="o1",
            email="user@example.com",
            code_hash=hash_otp("111111"),
            purpose="registration",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            attempts=0,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=otp_record)
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(ValidationError) as exc_info:
            await auth_service.verify_otp_and_create_user(
                email="user@example.com",
                otp_plain="999999",
                password="SecurePass1",
                db=db,
            )
        assert "Invalid" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_expired_otp_raises_validation_error(self) -> None:
        db = _make_db_session()
        # No valid OTP in DB (expired/consumed)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(ValidationError) as exc_info:
            await auth_service.verify_otp_and_create_user(
                email="user@example.com",
                otp_plain="123456",
                password="SecurePass1",
                db=db,
            )
        assert "expired" in exc_info.value.message.lower()


class TestLogin:
    @pytest.mark.asyncio
    async def test_wrong_password_raises_auth_error(self) -> None:
        db = _make_db_session()
        user = User(
            id="u1",
            email="user@example.com",
            password_hash=hash_password("correct_password"),
            email_verified_at=datetime.now(UTC),
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=user)
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(AuthenticationError):
            await auth_service.login_user("user@example.com", "wrong_password", db)

    @pytest.mark.asyncio
    async def test_unverified_user_raises_auth_error(self) -> None:
        db = _make_db_session()
        user = User(
            id="u1",
            email="user@example.com",
            password_hash=hash_password("correct_password"),
            email_verified_at=None,  # not verified
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=user)
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.login_user("user@example.com", "correct_password", db)
        assert "not verified" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_nonexistent_user_raises_auth_error(self) -> None:
        db = _make_db_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(AuthenticationError):
            await auth_service.login_user("nobody@example.com", "password", db)


# ── Quota service unit tests ──────────────────────────────────────────────────

class TestQuotaService:
    @pytest.mark.asyncio
    async def test_registered_user_has_unlimited_quota(self) -> None:
        from app.modules.auth.dependencies import Identity
        from app.modules.quota import service as quota_service

        db = AsyncMock()
        user = User(id="u1", email="x@example.com")
        identity = Identity(user=user, anon_session_id=None)

        status = await quota_service.get_quota_status(identity, db)
        assert not status.requires_auth
        assert status.remaining > 1000

    @pytest.mark.asyncio
    async def test_anon_with_no_record_gets_full_quota(self) -> None:
        from app.modules.auth.dependencies import Identity
        from app.modules.quota import service as quota_service
        from app.core.settings import settings

        db = AsyncMock()
        identity = Identity(user=None, anon_session_id=None)

        status = await quota_service.get_quota_status(identity, db)
        assert status.used == 0
        assert status.limit == settings.anonymous_free_analyses
        assert not status.requires_auth

    @pytest.mark.asyncio
    async def test_quota_exceeded_raises(self) -> None:
        from app.modules.auth.dependencies import Identity
        from app.modules.quota import service as quota_service
        from app.modules.quota.models import AnonymousUsage
        from app.core.exceptions import QuotaExceededError
        from app.core.settings import settings

        db = AsyncMock()
        # Simulate a usage row at the limit
        usage = AnonymousUsage(
            anon_session_id="test-session",
            analyses_used=settings.anonymous_free_analyses,
        )
        result_mock = MagicMock()
        result_mock.scalar_one = MagicMock(return_value=usage)
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()

        identity = Identity(user=None, anon_session_id="test-session")

        with pytest.raises(QuotaExceededError):
            await quota_service.increment_quota(identity, None, db)


# ── Consent service unit tests ────────────────────────────────────────────────

class TestConsentService:
    @pytest.mark.asyncio
    async def test_consent_recorded_for_anon_identity(self) -> None:
        from app.modules.auth.dependencies import Identity
        from app.modules.compliance import service as consent_service
        from app.modules.compliance.models import ConsentEvent

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        # Simulate the flush assigning values (ORM normally does this on commit)
        added_event = None

        def capture_add(obj: object) -> None:
            nonlocal added_event
            added_event = obj
            if isinstance(obj, ConsentEvent):
                obj.id = "ce-1"
                from datetime import UTC, datetime
                obj.granted_at = datetime.now(UTC)

        db.add.side_effect = capture_add

        identity = Identity(user=None, anon_session_id="anon-abc")
        result = await consent_service.record_consent(identity, "audio_processing", db)

        assert result.consent_type == "audio_processing"
        assert added_event is not None
        assert isinstance(added_event, ConsentEvent)
        assert added_event.anon_session_id == "anon-abc"

    @pytest.mark.asyncio
    async def test_missing_consent_raises_authorization_error(self) -> None:
        from app.modules.auth.dependencies import Identity
        from app.modules.compliance import service as consent_service
        from app.core.exceptions import AuthorizationError

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        db.execute = AsyncMock(return_value=result_mock)

        identity = Identity(user=None, anon_session_id="anon-no-consent")

        with pytest.raises(AuthorizationError) as exc_info:
            await consent_service.require_audio_processing_consent(identity, db)
        assert "audio_processing" in exc_info.value.details.get("missing_consent", "")
