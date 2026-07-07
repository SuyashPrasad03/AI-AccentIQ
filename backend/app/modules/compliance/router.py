"""
Compliance router — consent + data management endpoints.

  POST /consent              — record a consent event
  GET  /consent/status       — check current consent status
  GET  /me/data-summary      — what data we hold for this user
  DELETE /me                  — delete account and all data (cascading erasure)
  POST /me/consent/withdraw  — withdraw audio processing consent
"""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.db.mysql.base import get_db
from app.modules.auth.dependencies import Identity, get_current_identity, get_current_user
from app.modules.auth.models import User
from app.modules.auth.security import generate_anon_session_id, sign_anon_session_id
from app.modules.compliance import service
from app.modules.compliance.deletion_service import delete_user_data
from app.modules.compliance.models import ConsentEvent, DataDeletionRequest
from app.modules.compliance.schemas import (
    ConsentEventOut,
    ConsentStatusResponse,
    DataSummaryResponse,
    RecordConsentRequest,
)
from app.modules.upload.models import Recording

router = APIRouter(tags=["compliance"])

_ANON_COOKIE = "anon_session_id"
_ANON_COOKIE_MAX_AGE = 365 * 24 * 3600


def _ensure_anon_session(identity: Identity, response: Response) -> Identity:
    if identity.is_authenticated or identity.anon_session_id is not None:
        return identity
    raw_id = generate_anon_session_id()
    signed = sign_anon_session_id(raw_id)
    response.set_cookie(
        key=_ANON_COOKIE, value=signed, httponly=True,
        secure=False, samesite="lax", max_age=_ANON_COOKIE_MAX_AGE, path="/",
    )
    return Identity(user=None, anon_session_id=raw_id)


# ── Consent endpoints ─────────────────────────────────────────────────────────

@router.post(
    "/consent",
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
        identity=identity, consent_type=body.consent_type, db=db
    )


@router.get(
    "/consent/status",
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


# ── Data management endpoints (DPDP) ─────────────────────────────────────────

@router.get(
    "/me/data-summary",
    response_model=DataSummaryResponse,
    summary="View summary of all data held for this user",
)
async def get_data_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataSummaryResponse:
    """Shows exactly what data we hold — recordings count, storage, retention dates."""
    # Count recordings
    result = await db.execute(
        select(func.count()).select_from(Recording).where(
            Recording.user_id == current_user.id,
            Recording.deleted_at.is_(None),
        )
    )
    recordings_count = result.scalar() or 0

    # Count consent events
    result = await db.execute(
        select(func.count()).select_from(ConsentEvent).where(
            ConsentEvent.user_id == current_user.id,
        )
    )
    consent_count = result.scalar() or 0

    return DataSummaryResponse(
        user_id=current_user.id,
        email=current_user.email,
        recordings_count=recordings_count,
        consent_events_count=consent_count,
        audio_retention_days=30,
        account_created_at=current_user.created_at,
    )


@router.delete(
    "/me",
    status_code=200,
    summary="Delete account and all associated data (Right to Erasure)",
)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cascading deletion: MySQL user (soft-delete PII), recordings, Mongo docs,
    file storage, refresh tokens. Logged in data_deletion_requests for DPDP audit.
    """
    # Perform cascading deletion
    summary = await delete_user_data(current_user.id, db)

    # Log the deletion request
    deletion_record = DataDeletionRequest(
        user_id=current_user.id,
        completed_at=datetime.now(UTC),
        summary=json.dumps(summary, default=str),
    )
    db.add(deletion_record)
    await db.flush()

    return {
        "message": "Your account and all associated data have been permanently deleted.",
        "summary": summary,
    }


@router.post(
    "/me/consent/withdraw",
    status_code=200,
    summary="Withdraw audio processing consent",
)
async def withdraw_consent(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Withdraws audio_processing consent. Blocks further uploads until re-consented.
    Does NOT delete existing data — use DELETE /me for full erasure.
    """
    # Remove audio_processing consent events for this user
    from sqlalchemy import delete as sql_delete

    await db.execute(
        sql_delete(ConsentEvent).where(
            ConsentEvent.user_id == current_user.id,
            ConsentEvent.consent_type == "audio_processing",
        )
    )
    await db.flush()

    return {
        "message": "Audio processing consent withdrawn. You will need to re-consent before uploading new recordings.",
    }
