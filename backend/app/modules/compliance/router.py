"""
Compliance router — /consent/* endpoints.

  POST /consent            — record a consent event for the current identity
  GET  /consent/status     — check what the identity has already consented to
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql.base import get_db
from app.modules.auth.dependencies import Identity, get_current_identity
from app.modules.auth.security import generate_anon_session_id, sign_anon_session_id
from app.modules.compliance import service
from app.modules.compliance.schemas import (
    ConsentEventOut,
    ConsentStatusResponse,
    RecordConsentRequest,
)

router = APIRouter(prefix="/consent", tags=["compliance"])

_ANON_COOKIE = "anon_session_id"
_ANON_COOKIE_MAX_AGE = 365 * 24 * 3600


def _ensure_anon_session(identity: Identity, response: Response) -> Identity:
    """Assign an anonymous session cookie if the caller doesn't have one yet."""
    if identity.is_authenticated or identity.anon_session_id is not None:
        return identity

    raw_id = generate_anon_session_id()
    signed = sign_anon_session_id(raw_id)
    response.set_cookie(
        key=_ANON_COOKIE,
        value=signed,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=_ANON_COOKIE_MAX_AGE,
        path="/",
    )
    return Identity(user=None, anon_session_id=raw_id)


@router.post(
    "",
    response_model=ConsentEventOut,
    status_code=201,
    summary="Record a consent event (DPDP audit trail)",
)
async def record_consent(
    body: RecordConsentRequest,
    response: Response,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> ConsentEventOut:
    identity = _ensure_anon_session(identity, response)
    return await service.record_consent(
        identity=identity,
        consent_type=body.consent_type,
        db=db,
    )


@router.get(
    "/status",
    response_model=ConsentStatusResponse,
    summary="Check current consent status for the caller",
)
async def consent_status(
    response: Response,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> ConsentStatusResponse:
    identity = _ensure_anon_session(identity, response)
    return await service.get_consent_status(identity=identity, db=db)
