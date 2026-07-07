"""
MongoDB collection helpers for phoneme_analysis documents.
Full per-word/per-phoneme scoring breakdown stored here (large, nested).
"""

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.db.mongo.client import get_mongo_db

logger = get_logger(__name__)

COLLECTION = "phoneme_analysis"


async def insert_phoneme_analysis(
    recording_id: str,
    word_scores: list[dict],
    weak_phonemes: list[str],
    overall_score: float,
    accuracy_score: float,
    fluency_score: float,
) -> str:
    """Insert the full phoneme analysis into Mongo. Returns the document _id."""
    doc = {
        "_id": recording_id,  # keyed by recording for easy lookup
        "recording_id": recording_id,
        "words": word_scores,
        "weak_phonemes": weak_phonemes,
        "overall_score": overall_score,
        "accuracy_score": accuracy_score,
        "fluency_score": fluency_score,
        "created_at": datetime.now(UTC),
    }

    db = get_mongo_db()
    await db[COLLECTION].replace_one(
        {"_id": recording_id}, doc, upsert=True
    )

    logger.info(
        "phoneme_analysis_stored",
        recording_id=recording_id,
        word_count=len(word_scores),
        weak_phonemes=weak_phonemes,
    )
    return recording_id


async def get_phoneme_analysis(recording_id: str) -> dict | None:
    """Fetch the full phoneme analysis for a recording."""
    db = get_mongo_db()
    return await db[COLLECTION].find_one({"_id": recording_id})
