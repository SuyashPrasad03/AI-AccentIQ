"""
MongoDB cache collection for mistake explanations.

Cache key: "word|detected_issue|substitution_pattern"
e.g. "think|mispronounced|θ->t"

Same mistake pattern recurs across users → cache avoids redundant LLM calls.
"""

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.core.settings import settings
from app.db.mongo.client import get_mongo_db

logger = get_logger(__name__)

COLLECTION = "mistake_explanations"


def build_cache_key(word: str, detected_issue: str, substituted_as: list[str]) -> str:
    """Build a deterministic cache key from the mistake pattern."""
    sub_str = ",".join(substituted_as) if substituted_as else "none"
    return f"{word.lower().strip()}|{detected_issue}|{sub_str}"


async def get_cached_explanation(cache_key: str) -> dict | None:
    """Look up a cached explanation by its cache key."""
    db = get_mongo_db()
    doc = await db[COLLECTION].find_one({"cache_key": cache_key})
    if doc:
        logger.info("explanation_cache_hit", cache_key=cache_key)
    return doc


async def store_explanation(
    cache_key: str,
    explanation: str,
    mouth_position_tip: str,
    practice_words: list[str],
    model_version: str,
) -> None:
    """Write-through cache: store an explanation after LLM generation."""
    db = get_mongo_db()
    doc = {
        "cache_key": cache_key,
        "explanation": explanation,
        "mouth_position_tip": mouth_position_tip,
        "practice_words": practice_words,
        "model_version": model_version,
        "created_at": datetime.now(UTC),
    }
    await db[COLLECTION].replace_one(
        {"cache_key": cache_key}, doc, upsert=True
    )
    logger.info("explanation_cached", cache_key=cache_key)
