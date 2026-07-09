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


async def get_quota_status(identity: Identity, db: AsyncSession, ip_hash: str | None = None) -> QuotaStatusResponse:
    """Return current quota usage for the identity."""
    if identity.is_authenticated:
        return QuotaStatusResponse(
            used=0,
            limit=_REGISTERED_LIMIT,
            requires_auth=False,
            remaining=_REGISTERED_LIMIT,
        )

    # Use IP hash as primary lookup (works cross-domain without cookies)
    lookup_key = identity.anon_session_id or ip_hash
    if not lookup_key:
        return QuotaStatusResponse(
            used=0,
            limit=settings.anonymous_free_analyses,
            requires_auth=False,
            remaining=settings.anonymous_free_analyses,
        )

    # Look up by either anon_session_id or ip_hash — order by most-used to get the "real" row
    from sqlalchemy import or_
    conditions = []
    if lookup_key:
        conditions.append(AnonymousUsage.anon_session_id == lookup_key)
    if ip_hash:
        conditions.append(AnonymousUsage.ip_hash == ip_hash)

    if not conditions:
        return QuotaStatusResponse(
            used=0,
            limit=settings.anonymous_free_analyses,
            requires_auth=False,
            remaining=settings.anonymous_free_analyses,
        )

    result = await db.execute(
        select(AnonymousUsage).where(
            or_(*conditions)
        ).order_by(AnonymousUsage.analyses_used.desc()).limit(1)
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
    Fetch or create an AnonymousUsage row.
    Uses ip_hash as fallback lookup when anon_session_id isn't available (cross-domain).
    Orders by analyses_used DESC to always return the row with highest usage (prevents
    quota bypass from duplicate rows).
    """
    from sqlalchemy import or_

    # Try to find existing by session OR ip_hash
    conditions = []
    if anon_session_id:
        conditions.append(AnonymousUsage.anon_session_id == anon_session_id)
    if ip_hash:
        conditions.append(AnonymousUsage.ip_hash == ip_hash)

    if conditions:
        result = await db.execute(
            select(AnonymousUsage)
            .where(or_(*conditions))
            .order_by(AnonymousUsage.analyses_used.desc())
            .limit(1)
        )
        usage = result.scalar_one_or_none()
        if usage:
            # Update ip_hash if it wasn't set before
            if ip_hash and not usage.ip_hash:
                usage.ip_hash = ip_hash
            return usage

    # Create new row — handle potential unique constraint violation
    from sqlalchemy.exc import IntegrityError
    usage = AnonymousUsage(
        anon_session_id=anon_session_id or (ip_hash or "unknown"),
        ip_hash=ip_hash,
        analyses_used=0,
    )
    db.add(usage)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        # Race condition or duplicate — re-fetch
        if conditions:
            result = await db.execute(
                select(AnonymousUsage)
                .where(or_(*conditions))
                .order_by(AnonymousUsage.analyses_used.desc())
                .limit(1)
            )
            usage = result.scalar_one_or_none()
            if usage:
                return usage
        # Absolute fallback — create with unique ID
        import uuid
        usage = AnonymousUsage(
            anon_session_id=str(uuid.uuid4()),
            ip_hash=ip_hash,
            analyses_used=0,
        )
        db.add(usage)
        await db.flush()
    return usage
