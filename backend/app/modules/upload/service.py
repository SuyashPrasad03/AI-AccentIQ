"""
Upload service — orchestrates the full upload pipeline:

  1. Validate MIME type (magic bytes)
  2. Validate file size
  3. Write to temp file → validate duration via ffprobe
  4. Normalize to 16kHz mono WAV via FFmpeg
  5. Persist normalized file via storage backend
  6. Create recordings DB row
  7. Increment quota counter

Each step can raise a clear ValidationError / QuotaExceededError.
"""

import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.dependencies import Identity
from app.modules.upload.models import Recording
from app.modules.upload.preprocessing import normalize_audio
from app.modules.upload.storage.local_disk import get_storage_backend
from app.modules.upload.validators import (
    get_audio_duration,
    validate_duration,
    validate_file_size,
    validate_mime_type,
)

logger = get_logger(__name__)


async def process_upload(
    file_bytes: bytes,
    content_type: str | None,
    identity: Identity,
    ip_hash: str | None,
    db: AsyncSession,
) -> Recording:
    """
    Full upload pipeline. Assumes quota and consent checks have already passed
    (enforced at the router level).

    Returns the persisted Recording ORM object.
    """
    # 1. MIME validation (sniff actual bytes, don't trust header)
    validate_mime_type(content_type, file_bytes)

    # 2. File size check
    validate_file_size(len(file_bytes))

    # 3. Write to temp file for ffprobe/ffmpeg processing
    temp_input = Path(tempfile.mktemp(suffix=".upload"))
    temp_input.write_bytes(file_bytes)

    try:
        # 4. Get authoritative duration from ffprobe
        duration = get_audio_duration(temp_input)

        # 5. Validate duration is within acceptable range
        validate_duration(duration)

        # 6. Normalize to 16kHz mono WAV
        normalized_path = normalize_audio(temp_input)

    finally:
        # Clean up the raw temp upload regardless of success/failure
        if temp_input.exists():
            temp_input.unlink()

    # 7. Persist the normalized file via storage backend
    storage = get_storage_backend()
    normalized_bytes = normalized_path.read_bytes()
    filename = f"{uuid.uuid4().hex}.wav"

    try:
        relative_path = await storage.save(
            data=normalized_bytes,
            filename=filename,
            subdirectory="recordings",
        )
    finally:
        # Clean up temp normalized file
        if normalized_path.exists():
            normalized_path.unlink()

    # 8. Create DB record
    recording = Recording(
        user_id=identity.user_id,
        anon_session_id=identity.anon_session_id if not identity.is_authenticated else None,
        storage_path=relative_path,
        duration_seconds=duration,
        status="uploaded",
        created_at=datetime.now(UTC),
    )
    db.add(recording)
    await db.flush()

    logger.info(
        "recording_uploaded",
        recording_id=recording.id,
        identity=identity.display_name,
        duration=duration,
        storage_path=relative_path,
    )

    # 9. Increment quota (for anonymous users)
    from app.modules.quota.service import increment_quota
    await increment_quota(identity=identity, ip_hash=ip_hash, db=db)

    return recording
