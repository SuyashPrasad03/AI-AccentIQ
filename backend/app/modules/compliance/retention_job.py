"""
Retention purge job — automatically deletes audio past its retention window.

Runs as a scheduled background task (APScheduler or cron endpoint).
Only purges AUDIO FILES — derived data (scores, transcripts) is retained
as the user's progress history (less sensitive than raw biometric-adjacent audio).

DPDP compliance: raw audio auto-deleted after AUDIO_RETENTION_DAYS (default 30).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.settings import settings
from app.db.mysql.base import AsyncSessionLocal
from app.modules.upload.models import Recording
from app.modules.upload.storage.local_disk import get_storage_backend

logger = get_logger(__name__)


async def run_retention_purge() -> dict:
    """
    Find and delete all audio files past their retention window.
    Only deletes the file from storage and marks the recording's file as purged.

    Returns a summary of what was purged.
    """
    cutoff = datetime.now(UTC) - timedelta(days=settings.audio_retention_days)
    summary = {"purged_count": 0, "errors": 0, "cutoff": cutoff.isoformat()}

    async with AsyncSessionLocal() as db:
        # Find recordings older than retention period that still have files
        result = await db.execute(
            select(Recording).where(
                Recording.created_at < cutoff,
                Recording.deleted_at.is_(None),
                Recording.storage_path.isnot(None),
                Recording.storage_path != "",
            )
        )
        expired_recordings = result.scalars().all()

        if not expired_recordings:
            logger.info("retention_purge_nothing_to_do", cutoff=cutoff.isoformat())
            return summary

        storage = get_storage_backend()

        for recording in expired_recordings:
            try:
                deleted = await storage.delete(recording.storage_path)
                if deleted:
                    # Mark file as purged (clear storage path, keep the record for history)
                    await db.execute(
                        update(Recording)
                        .where(Recording.id == recording.id)
                        .values(storage_path="[purged]")
                    )
                    summary["purged_count"] += 1
                    logger.info(
                        "retention_file_purged",
                        recording_id=recording.id,
                        original_path=recording.storage_path,
                    )
            except Exception as exc:
                summary["errors"] += 1
                logger.error(
                    "retention_purge_error",
                    recording_id=recording.id,
                    error=str(exc),
                )

        await db.commit()

    logger.info("retention_purge_complete", **summary)
    return summary
