"""
Quota router — /quota/* endpoints.

  GET  /quota/status   — return current usage for the caller
  POST /quota/increment — stub endpoint for Phase 2 manual testing
                         (Phase 3 replaces this with the real upload gate)
"""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql.base import get_db
from app.modules.auth.dependencies import Identity, get_current_identity
from app.modules.auth.security import (
    compute_ip_hash,
    generate_anon_session_id,
    sign_anon_session_id,
)
from app.modules.quota import service
from app.modules.quota.schemas import IncrementResponse, QuotaStatusResponse

router = APIRouter(prefix="/quota", tags=["quota"])

_ANON_COOKIE = "anon_session_id"
_ANON_COOKIE_MAX_AGE = 365 * 24 * 3600  # 1 year


def _ensure_anon_cookie(identity: Identity, request: Request, response: Response) -> Identity:
    """
    Assign a new anon_session_id cookie if the caller is anonymous with no session.
    Returns a (possibly new) Identity with anon_session_id populated.
    """
    if identity.is_authenticated or identity.anon_session_id is not None:
        return identity

    raw_id = generate_anon_session_id()
    signed = sign_anon_session_id(raw_id)
    response.set_cookie(
        key=_ANON_COOKIE,
        value=signed,
        httponly=True,
        secure=False,   # dev; Phase 11 sets secure=True in production
        samesite="lax",
        max_age=_ANON_COOKIE_MAX_AGE,
        path="/",
    )
    return Identity(user=None, anon_session_id=raw_id)


@router.get(
    "/status",
    response_model=QuotaStatusResponse,
    summary="Current usage quota for the caller",
)
async def quota_status(
    request: Request,
    response: Response,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> QuotaStatusResponse:
    identity = _ensure_anon_cookie(identity, request, response)
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    ip_hash = compute_ip_hash(ip, ua)
    return await service.get_quota_status(identity=identity, db=db, ip_hash=ip_hash)


@router.post(
    "/increment",
    response_model=IncrementResponse,
    summary="[Phase 2 stub] Manually increment the usage counter",
    description=(
        "Test-only endpoint that simulates a completed analysis. "
        "Replaced by the real upload pipeline in Phase 3."
    ),
)
async def increment_quota_stub(
    request: Request,
    response: Response,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> IncrementResponse:
    identity = _ensure_anon_cookie(identity, request, response)

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    ip_hash = compute_ip_hash(ip, ua) if not identity.is_authenticated else None

    return await service.increment_quota(
        identity=identity,
        ip_hash=ip_hash,
        db=db,
    )
