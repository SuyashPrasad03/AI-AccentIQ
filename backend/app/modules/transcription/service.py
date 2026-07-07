"""
Transcription service — orchestrates the background transcription job.

Called as a FastAPI BackgroundTask after upload completes.
Production upgrade path: Celery + Redis for distributed job processing.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.mongo.transcripts import insert_transcript, get_transcript_by_recording_id
from app.db.mysql.base import AsyncSessionLocal
from app.modules.transcription.schemas import TranscriptResponse
from app.modules.transcription.whisperx_client import transcribe_and_align
from app.modules.upload.models import Recording
from app.modules.upload.storage.local_disk import get_storage_backend

logger = get_logger(__name__)


async def run_transcription_job(recording_id: str) -> None:
    """
    Background job: transcribe + align a recording, store result in Mongo,
    update MySQL status.

    This runs outside the request lifecycle — it manages its own DB session.
    On failure, sets status=failed with an error reason (never hangs silently).
    """
    logger.info("transcription_job_start", recording_id=recording_id)

    async with AsyncSessionLocal() as db:
        try:
            # 1. Mark as processing
            await db.execute(
                update(Recording)
                .where(Recording.id == recording_id)
                .values(status="processing")
            )
            await db.commit()

            # 2. Load recording to get storage path
            result = await db.execute(
                select(Recording).where(Recording.id == recording_id)
            )
            recording = result.scalar_one_or_none()
            if recording is None:
                logger.error("transcription_recording_not_found", recording_id=recording_id)
                return

            # 3. Resolve full audio path
            storage = get_storage_backend()
            audio_path = storage.get_full_path(recording.storage_path)

            # 4. Run WhisperX transcription + alignment
            transcript_data = transcribe_and_align(audio_path)

            # 5. Store in MongoDB
            transcript_id = str(uuid.uuid4())
            await insert_transcript(
                transcript_id=transcript_id,
                recording_id=recording_id,
                raw_text=transcript_data["raw_text"],
                words=transcript_data["words"],
                language=transcript_data["language"],
                model_version=transcript_data["model_version"],
            )

            # 6. Update MySQL with transcript pointer + status
            await db.execute(
                update(Recording)
                .where(Recording.id == recording_id)
                .values(
                    status="transcribed",
                    mongo_transcript_id=transcript_id,
                )
            )
            await db.commit()

            logger.info(
                "transcription_job_done",
                recording_id=recording_id,
                transcript_id=transcript_id,
                word_count=len(transcript_data["words"]),
            )

            # 7. Trigger scoring pipeline (chained background job)
            from app.modules.scoring.service import run_scoring_job
            await run_scoring_job(recording_id)

        except Exception as exc:
            # On any failure: mark as failed, store error reason, never hang
            logger.error(
                "transcription_job_failed",
                recording_id=recording_id,
                error=str(exc),
                exc_info=True,
            )
            try:
                await db.rollback()
                await db.execute(
                    update(Recording)
                    .where(Recording.id == recording_id)
                    .values(status="failed")
                )
                await db.commit()
            except Exception as inner_exc:
                logger.error(
                    "transcription_status_update_failed",
                    recording_id=recording_id,
                    error=str(inner_exc),
                )


async def get_transcript_for_recording(
    recording_id: str,
) -> TranscriptResponse | None:
    """
    Fetch the transcript from Mongo for a given recording.
    Returns None if not yet available.
    """
    doc = await get_transcript_by_recording_id(recording_id)
    if doc is None:
        return None

    return TranscriptResponse(
        recording_id=doc.recording_id,
        raw_text=doc.raw_text,
        words=doc.words,
        language=doc.language,
        model_version=doc.model_version,
    )
