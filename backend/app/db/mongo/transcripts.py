"""
MongoDB collection helpers for transcripts.

Collection: `transcripts`
Document shape validated by TranscriptDocument (Pydantic) before insert.
"""

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.db.mongo.client import get_mongo_db
from app.modules.transcription.schemas import TranscriptDocument, WordSegment

logger = get_logger(__name__)

COLLECTION = "transcripts"


async def insert_transcript(
    transcript_id: str,
    recording_id: str,
    raw_text: str,
    words: list[dict],
    language: str,
    model_version: str,
) -> TranscriptDocument:
    """
    Validate and insert a transcript document into MongoDB.
    Returns the validated Pydantic model.
    """
    # Validate word segments through Pydantic
    validated_words = [WordSegment(**w) for w in words]

    doc = TranscriptDocument(
        _id=transcript_id,
        recording_id=recording_id,
        raw_text=raw_text,
        words=validated_words,
        language=language,
        model_version=model_version,
        created_at=datetime.now(UTC),
    )

    db = get_mongo_db()
    # Convert to dict for mongo insertion (use by_alias to keep _id)
    mongo_doc = doc.model_dump(by_alias=True)
    await db[COLLECTION].insert_one(mongo_doc)

    logger.info(
        "transcript_inserted",
        transcript_id=transcript_id,
        recording_id=recording_id,
        word_count=len(validated_words),
    )
    return doc


async def get_transcript_by_recording_id(recording_id: str) -> TranscriptDocument | None:
    """Fetch a transcript by its associated recording ID."""
    db = get_mongo_db()
    doc = await db[COLLECTION].find_one({"recording_id": recording_id})
    if doc is None:
        return None
    return TranscriptDocument(**doc)


async def get_transcript_by_id(transcript_id: str) -> TranscriptDocument | None:
    """Fetch a transcript by its _id."""
    db = get_mongo_db()
    doc = await db[COLLECTION].find_one({"_id": transcript_id})
    if doc is None:
        return None
    return TranscriptDocument(**doc)
