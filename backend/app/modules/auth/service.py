"""
Auth service — business logic layer.

Keeps all DB interactions and security operations out of the router.
Every public method maps 1-to-1 with an endpoint operation.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_otp_email
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.core.rate_limit import otp_rate_limiter
from app.core.settings import settings
from app.modules.auth.models import OtpCode, RefreshToken, User
from app.modules.auth.security import (
    create_access_token,
    generate_otp,
    generate_refresh_token,
    hash_otp,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_otp,
    verify_password,
)
from app.modules.auth.schemas import TokenResponse, UserOut

logger = get_logger(__name__)

# Max OTP verification attempts before the code is locked
_MAX_OTP_ATTEMPTS = 5


async def register_user(email: str, db: AsyncSession, background_tasks=None) -> str:
    """
    Initiate registration: check email not taken, send OTP.
    Returns the email for the response message.

    If the user already exists but is unverified, we resend the OTP
    (allows recovery from dropped emails).
    """
    # Check rate limit first
    if not otp_rate_limiter.is_allowed(email):
        raise ValidationError(
            message="Too many verification codes requested. Please wait before trying again.",
            details={"retry_after_seconds": 3600},
        )

    # Check for existing verified user
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    existing = result.scalar_one_or_none()

    if existing and existing.email_verified_at is not None:
        raise ConflictError(
            message="An account with this email already exists.",
            details={"email": email},
        )

    # If unverified account already exists, we'll reuse it (just resend OTP).
    # Mark any previous unexpired OTPs as consumed so old codes no longer work.
    await _invalidate_pending_otps(email, db)

    # Generate + persist new OTP
    otp_plain = generate_otp()
    otp_record = OtpCode(
        email=email,
        code_hash=hash_otp(otp_plain),
        purpose="registration",
        expires_at=datetime.now(UTC) + timedelta(minutes=settings.otp_expiry_minutes),
    )
    db.add(otp_record)
    await db.flush()

    otp_rate_limiter.record(email)
    logger.info("otp_sent", email=email, purpose="registration")

    # Send email in background (non-blocking) to avoid timeout on platforms like Render
    if background_tasks:
        background_tasks.add_task(send_otp_email, to=email, otp=otp_plain, purpose="registration")
    else:
        await send_otp_email(to=email, otp=otp_plain, purpose="registration")

    return email


async def verify_otp_and_create_user(
    email: str,
    otp_plain: str,
    password: str,
    db: AsyncSession,
) -> tuple[User, str, str]:
    """
    Verify the OTP, create (or update) the user with the hashed password,
    issue access + refresh tokens.

    Returns (user, access_token, refresh_token_plain).
    """
    otp_record = await _get_valid_otp(email, db)

    # Increment attempt count atomically before verification
    otp_record.attempts += 1

    if not verify_otp(otp_plain, otp_record.code_hash):
        logger.warning("otp_invalid", email=email, attempts=otp_record.attempts)
        if otp_record.attempts >= _MAX_OTP_ATTEMPTS:
            otp_record.consumed_at = datetime.now(UTC)  # lock it out
            raise ValidationError(
                message="Too many failed attempts. Please request a new code.",
                details={"email": email},
            )
        raise ValidationError(
            message="Invalid verification code.",
            details={"attempts_remaining": _MAX_OTP_ATTEMPTS - otp_record.attempts},
        )

    # Mark OTP as consumed
    otp_record.consumed_at = datetime.now(UTC)

    # Upsert user
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    now = datetime.now(UTC)

    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            email_verified_at=now,
            created_at=now,
        )
        db.add(user)
    else:
        user.password_hash = hash_password(password)
        user.email_verified_at = now

    await db.flush()

    access_token, refresh_plain = await _issue_tokens(user, db)
    logger.info("user_registered", user_id=user.id, email=email)
    return user, access_token, refresh_plain


async def login_user(
    email: str,
    password: str,
    db: AsyncSession,
) -> tuple[User, str, str]:
    """
    Validate credentials, issue tokens.
    Returns (user, access_token, refresh_token_plain).
    """
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None:
        raise AuthenticationError(message="Invalid email or password.")

    if user.email_verified_at is None:
        raise AuthenticationError(
            message="Email not verified. Please complete registration first."
        )

    if not verify_password(password, user.password_hash):
        raise AuthenticationError(message="Invalid email or password.")

    access_token, refresh_plain = await _issue_tokens(user, db)
    logger.info("user_logged_in", user_id=user.id)
    return user, access_token, refresh_plain


async def refresh_access_token(
    refresh_token_plain: str,
    db: AsyncSession,
) -> tuple[User, str, str]:
    """
    Validate a refresh token cookie, issue a new access + refresh token pair
    (token rotation — old token is revoked).

    Returns (user, new_access_token, new_refresh_token_plain).
    """
    token_hash = hash_refresh_token(refresh_token_plain)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    record = result.scalar_one_or_none()

    if record is None:
        raise AuthenticationError(message="Invalid or expired refresh token.")

    # Load the user
    user_result = await db.execute(
        select(User).where(User.id == record.user_id, User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError(message="User not found.")

    # Revoke the old token (rotation)
    record.revoked_at = datetime.now(UTC)

    # Issue a new pair
    new_access, new_refresh_plain = await _issue_tokens(user, db)
    logger.info("token_refreshed", user_id=user.id)
    return user, new_access, new_refresh_plain


async def logout_user(refresh_token_plain: str, db: AsyncSession) -> None:
    """Revoke the given refresh token."""
    token_hash = hash_refresh_token(refresh_token_plain)
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    logger.info("user_logged_out")


async def get_user_by_id(user_id: str, db: AsyncSession) -> User:
    """Fetch a non-deleted user by ID, or raise NotFoundError."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError(message="User not found.")
    return user


# ── Private helpers ───────────────────────────────────────────────────────────

async def _get_valid_otp(email: str, db: AsyncSession) -> OtpCode:
    """
    Fetch the most recent, unexpired, unconsumed OTP for this email.
    Raises ValidationError if none exists.
    """
    result = await db.execute(
        select(OtpCode)
        .where(
            OtpCode.email == email,
            OtpCode.consumed_at.is_(None),
            OtpCode.expires_at > datetime.now(UTC),
            OtpCode.attempts < _MAX_OTP_ATTEMPTS,
        )
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise ValidationError(
            message="Verification code not found, expired, or already used. "
                    "Please request a new one.",
            details={"email": email},
        )
    return record


async def _invalidate_pending_otps(email: str, db: AsyncSession) -> None:
    """Mark all pending OTPs for this email as consumed."""
    result = await db.execute(
        select(OtpCode).where(
            OtpCode.email == email,
            OtpCode.consumed_at.is_(None),
        )
    )
    for record in result.scalars().all():
        record.consumed_at = datetime.now(UTC)


async def _issue_tokens(user: User, db: AsyncSession) -> tuple[str, str]:
    """Create an access token and persist a new refresh token. Returns both."""
    access_token = create_access_token(user.id)
    refresh_plain = generate_refresh_token()

    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_plain),
        expires_at=refresh_token_expiry(),
    )
    db.add(refresh_record)
    await db.flush()

    return access_token, refresh_plain
