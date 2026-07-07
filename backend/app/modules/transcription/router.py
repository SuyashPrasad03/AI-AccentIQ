"""
Transcription router — polling and transcript retrieval endpoints.

  GET /recordings/{id}/status     — poll processing status
  GET /recordings/{id}/transcript — get the full transcript (after processing)
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.db.mysql.base import get_db
from app.modules.auth.dependencies import Identity, get_current_identity
from app.modules.transcription import service
from app.modules.transcription.schemas import RecordingStatusResponse, TranscriptResponse
from app.modules.upload.models import Recording

router = APIRouter(prefix="/recordings", tags=["transcription"])


async def _get_owned_recording(
    recording_id: str,
    identity: Identity,
    db: AsyncSession,
) -> Recording:
    """Fetch a recording and verify ownership. Raises 404 or 403."""
    result = await db.execute(
        select(Recording).where(
            Recording.id == recording_id,
            Recording.deleted_at.is_(None),
        )
    )
    recording = result.scalar_one_or_none()
    if recording is None:
        raise NotFoundError(message="Recording not found.")

    # Owner check
    if identity.is_authenticated:
        if recording.user_id != identity.user_id:
            raise AuthorizationError(message="You don't have access to this recording.")
    else:
        if recording.anon_session_id != identity.anon_session_id:
            raise AuthorizationError(message="You don't have access to this recording.")

    return recording


@router.get(
    "/{recording_id}/status",
    response_model=RecordingStatusResponse,
    summary="Poll the processing status of a recording",
)
async def get_recording_status(
    recording_id: str,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> RecordingStatusResponse:
    """
    Frontend polls this endpoint to know when transcription is complete.
    Typical status flow: uploaded → processing → transcribed → scored
    """
    recording = await _get_owned_recording(recording_id, identity, db)
    return RecordingStatusResponse(
        recording_id=recording.id,
        status=recording.status,
        error_reason=None,  # Phase 10 adds a dedicated error column
        duration_seconds=recording.duration_seconds,
        created_at=recording.created_at,
    )


@router.get(
    "/{recording_id}/transcript",
    response_model=TranscriptResponse,
    summary="Get the full transcript for a recording",
)
async def get_transcript(
    recording_id: str,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> TranscriptResponse:
    """
    Returns the word-level timestamped transcript from MongoDB.
    Only available after status transitions to 'transcribed' or later.
    """
    await _get_owned_recording(recording_id, identity, db)

    transcript = await service.get_transcript_for_recording(recording_id)
    if transcript is None:
        raise NotFoundError(
            message="Transcript not yet available. Recording may still be processing.",
            details={"recording_id": recording_id},
        )
    return transcript
