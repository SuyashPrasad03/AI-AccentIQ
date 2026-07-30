"""
MongoDB collection helpers for phoneme_analysis documents.
Full per-word/per-phoneme scoring breakdown stored here (large, nested).

Phase 24 additions:
  - gop_raw_scores: per-word array of raw GOP log-probability scores
  - gop_confidence: mean raw GOP score (for quick filtering/comparison)
  - scoring_engine_version: "gop" | "legacy" (which engine produced the stored result)
"""

from datetime import UTC, datetime
from typing import Any

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
    scoring_engine_version: str | None = None,
    gop_raw_scores: list[dict] | None = None,
    gop_confidence: float | None = None,
) -> str:
    """Insert the full phoneme analysis into Mongo. Returns the document _id."""
    doc: dict[str, Any] = {
        "_id": recording_id,
        "recording_id": recording_id,
        "words": word_scores,
        "weak_phonemes": weak_phonemes,
        "overall_score": overall_score,
        "accuracy_score": accuracy_score,
        "fluency_score": fluency_score,
        "created_at": datetime.now(UTC),
    }

    # Phase 24 fields
    if scoring_engine_version:
        doc["scoring_engine_version"] = scoring_engine_version
    if gop_raw_scores is not None:
        doc["gop_raw_scores"] = gop_raw_scores
    if gop_confidence is not None:
        doc["gop_confidence"] = gop_confidence

    db = get_mongo_db()
    await db[COLLECTION].replace_one(
        {"_id": recording_id}, doc, upsert=True
    )

    logger.info(
        "phoneme_analysis_stored",
        recording_id=recording_id,
        word_count=len(word_scores),
        weak_phonemes=weak_phonemes,
        scoring_engine=scoring_engine_version,
    )
    return recording_id


async def get_phoneme_analysis(recording_id: str) -> dict | None:
    """Fetch the full phoneme analysis for a recording."""
    db = get_mongo_db()
    return await db[COLLECTION].find_one({"_id": recording_id})
