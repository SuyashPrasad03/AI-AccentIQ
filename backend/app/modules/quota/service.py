"""
Quota service — tracks analyses used per identity (anon or registered).

Anonymous users are limited to `settings.anonymous_free_analyses` (default 3).
Registered users have unlimited quota in Phase 2 (tiered plans are out of scope).

Key design: the counter is authoritative server-side, never just a cookie count.
The anon_session_id + ip_hash dual-key approach raises the bar for trivial bypass
without full device fingerprinting (which DPDP deliberately avoids).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import QuotaExceededError
from app.core.logging import get_logger
from app.core.settings import settings
from app.modules.auth.dependencies import Identity
from app.modules.quota.models import AnonymousUsage
from app.modules.quota.schemas import IncrementResponse, QuotaStatusResponse

logger = get_logger(__name__)

# Registered users are treated as "unlimited" for now (no paid tier yet)
_REGISTERED_LIMIT = 999_999


async def get_quota_status(identity: Identity, db: AsyncSession) -> QuotaStatusResponse:
    """Return current quota usage for the identity."""
    if identity.is_authenticated:
        return QuotaStatusResponse(
            used=0,
            limit=_REGISTERED_LIMIT,
            requires_auth=False,
            remaining=_REGISTERED_LIMIT,
        )

    if identity.anon_session_id is None:
        # Brand-new anonymous visitor — no record yet, return defaults immediately
        return QuotaStatusResponse(
            used=0,
            limit=settings.anonymous_free_analyses,
            requires_auth=False,
            remaining=settings.anonymous_free_analyses,
        )

    # Look up existing row; if absent, that means zero usage
    result = await db.execute(
        select(AnonymousUsage).where(
            AnonymousUsage.anon_session_id == identity.anon_session_id
        )
    )
    usage = result.scalar_one_or_none()
    used = usage.analyses_used if usage else 0
    limit = settings.anonymous_free_analyses
    return QuotaStatusResponse(
        used=used,
        limit=limit,
        requires_auth=(used >= limit),
        remaining=max(0, limit - used),
    )


async def increment_quota(
    identity: Identity,
    ip_hash: str | None,
    db: AsyncSession,
) -> IncrementResponse:
    """
    Increment the usage counter for this identity.
    Raises QuotaExceededError if the anonymous limit has been reached.

    For registered users, always succeeds (unlimited quota in Phase 2).
    """
    if identity.is_authenticated:
        return IncrementResponse(
            used=1,
            limit=_REGISTERED_LIMIT,
            remaining=_REGISTERED_LIMIT - 1,
            quota_exceeded=False,
        )

    if identity.anon_session_id is None:
        # Should not happen in normal flow — caller should have assigned a session
        raise QuotaExceededError()

    usage = await _get_or_create_usage(identity.anon_session_id, ip_hash, db)
    limit = settings.anonymous_free_analyses

    if usage.analyses_used >= limit:
        logger.info(
            "quota_exceeded",
            anon_session_id=identity.anon_session_id,
            used=usage.analyses_used,
        )
        raise QuotaExceededError(
            message=(
                f"You have used all {limit} free analyses. "
                "Please register to continue."
            )
        )

    usage.analyses_used += 1
    await db.flush()

    logger.info(
        "quota_incremented",
        anon_session_id=identity.anon_session_id,
        used=usage.analyses_used,
    )
    return IncrementResponse(
        used=usage.analyses_used,
        limit=limit,
        remaining=max(0, limit - usage.analyses_used),
        quota_exceeded=(usage.analyses_used >= limit),
    )


async def check_quota_or_raise(identity: Identity, db: AsyncSession) -> None:
    """
    Used as a guard in upload/analysis endpoints:
    raise QuotaExceededError if the anonymous user is over limit, no-op otherwise.
    """
    if identity.is_authenticated:
        return

    status = await get_quota_status(identity, db)
    if status.requires_auth:
        raise QuotaExceededError(
            message=(
                f"You have used all {status.limit} free analyses. "
                "Please register to continue."
            )
        )


# ── Private helpers ───────────────────────────────────────────────────────────

async def _get_or_create_usage(
    anon_session_id: str,
    ip_hash: str | None,
    db: AsyncSession,
) -> AnonymousUsage:
    """
    Fetch or create an AnonymousUsage row for this session.
    Uses a simple SELECT-then-INSERT pattern for MySQL compatibility.
    """
    # Try to find existing
    result = await db.execute(
        select(AnonymousUsage).where(
            AnonymousUsage.anon_session_id == anon_session_id
        )
    )
    usage = result.scalar_one_or_none()

    if usage is None:
        # Create new row
        usage = AnonymousUsage(
            anon_session_id=anon_session_id,
            ip_hash=ip_hash,
            analyses_used=0,
        )
        db.add(usage)
        await db.flush()

    return usage
