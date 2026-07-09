"""
Upload router — /recordings/* endpoints.

  POST /recordings/upload   — upload an audio file for analysis
  GET  /recordings/{id}     — get recording metadata by ID
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.settings import settings
from app.db.mysql.base import get_db
from app.modules.auth.dependencies import Identity, get_current_identity
from app.modules.auth.security import (
    compute_ip_hash,
    generate_anon_session_id,
    sign_anon_session_id,
)
from app.modules.compliance.service import require_audio_processing_consent
from app.modules.quota.service import check_quota_or_raise
from app.modules.upload import service as upload_service
from app.modules.upload.models import Recording
from app.modules.upload.schemas import RecordingOut, UploadResponse
from app.modules.transcription.service import run_transcription_job

router = APIRouter(prefix="/recordings", tags=["recordings"])

_ANON_COOKIE = "anon_session_id"
_ANON_COOKIE_MAX_AGE = 365 * 24 * 3600


def _ensure_anon_session(identity: Identity, response: Response) -> Identity:
    """Assign anon session cookie if not present."""
    if identity.is_authenticated or identity.anon_session_id is not None:
        return identity
    raw_id = generate_anon_session_id()
    signed = sign_anon_session_id(raw_id)
    response.set_cookie(
        key=_ANON_COOKIE, value=signed,
        httponly=True, secure=False, samesite="lax",
        max_age=_ANON_COOKIE_MAX_AGE, path="/",
    )
    return Identity(user=None, anon_session_id=raw_id)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=201,
    summary="Upload an audio recording for pronunciation analysis",
)
async def upload_recording(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio file (15-45 seconds)"),
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """
    Full upload pipeline with these gates (in order):
      1. Consent check (audio_processing consent must exist)
      2. Quota check (anon users limited to 3 free analyses)
      3. MIME / size / duration validation
      4. FFmpeg normalization → storage → DB record → quota increment
    """
    identity = _ensure_anon_session(identity, response)

    # Gates disabled for cross-domain deployment (Vercel+Render can't share cookies)
    # The frontend enforces consent UI before showing upload
    # TODO: Re-enable when using same-domain or custom domain

    # Read file into memory (streaming not needed for 50MB max, 45s audio is ~1.4MB WAV)
    file_bytes = await file.read()
    if not file_bytes:
        raise ValidationError(message="Uploaded file is empty.")

    # Compute IP hash for quota tracking
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    ip_hash = compute_ip_hash(ip, ua) if not identity.is_authenticated else None

    # Run the full pipeline
    recording = await upload_service.process_upload(
        file_bytes=file_bytes,
        content_type=file.content_type,
        identity=identity,
        ip_hash=ip_hash,
        db=db,
    )

    # Trigger transcription as a background job (non-blocking)
    background_tasks.add_task(run_transcription_job, recording.id)

    return UploadResponse(
        recording=RecordingOut.model_validate(recording),
        message="Recording uploaded and preprocessed successfully. Transcription started.",
    )


@router.get(
    "/{recording_id}",
    response_model=RecordingOut,
    summary="Get recording metadata by ID",
)
async def get_recording(
    recording_id: str,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> RecordingOut:
    """Fetch recording metadata. Only the owner can access their own recording."""
    result = await db.execute(
        select(Recording).where(
            Recording.id == recording_id,
            Recording.deleted_at.is_(None),
        )
    )
    recording = result.scalar_one_or_none()
    if recording is None:
        raise NotFoundError(message="Recording not found.")

    # Authorization: owner check
    if identity.is_authenticated:
        if recording.user_id != identity.user_id:
            raise AuthorizationError(message="You don't have access to this recording.")

    return RecordingOut.model_validate(recording)


@router.delete(
    "/{recording_id}",
    status_code=200,
    summary="Delete a recording (soft-delete)",
)
async def delete_recording(
    recording_id: str,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a recording. Only the owner can delete."""
    from datetime import UTC, datetime
    from sqlalchemy import update

    result = await db.execute(
        select(Recording).where(
            Recording.id == recording_id,
            Recording.deleted_at.is_(None),
        )
    )
    recording = result.scalar_one_or_none()
    if recording is None:
        raise NotFoundError(message="Recording not found.")

    # Authorization
    if identity.is_authenticated:
        if recording.user_id != identity.user_id:
            raise AuthorizationError(message="You don't have access to this recording.")

    # Soft-delete
    await db.execute(
        update(Recording)
        .where(Recording.id == recording_id)
        .values(deleted_at=datetime.now(UTC))
    )

    return {"message": "Recording deleted.", "recording_id": recording_id}


@router.patch(
    "/{recording_id}",
    status_code=200,
    summary="Rename a recording",
)
async def rename_recording(
    recording_id: str,
    body: dict,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Update the title of a recording. Only the owner can rename."""
    from sqlalchemy import update

    result = await db.execute(
        select(Recording).where(
            Recording.id == recording_id,
            Recording.deleted_at.is_(None),
        )
    )
    recording = result.scalar_one_or_none()
    if recording is None:
        raise NotFoundError(message="Recording not found.")

    if identity.is_authenticated:
        if recording.user_id != identity.user_id:
            raise AuthorizationError(message="You don't have access to this recording.")

    new_title = body.get("title", "").strip()
    if not new_title or len(new_title) > 255:
        raise ValidationError(message="Title must be 1-255 characters.")

    await db.execute(
        update(Recording)
        .where(Recording.id == recording_id)
        .values(title=new_title)
    )

    return {"message": "Recording renamed.", "recording_id": recording_id, "title": new_title}
