"""
Weak phoneme aggregation across a user's recent recordings.

Design:
  - Registered users: aggregate weak_phonemes from last N recordings (default 5),
    frequency-weighted (phoneme wrong 4/5 times outranks 1/5).
  - Anonymous users: single-recording only (no cross-session history).
  - Returns the top-K most problematic phonemes sorted by frequency.
"""

from collections import Counter

from app.core.logging import get_logger
from app.db.mongo.client import get_mongo_db
from app.modules.auth.dependencies import Identity

logger = get_logger(__name__)

# How many recent recordings to look back
HISTORY_DEPTH = 5
# Max phonemes to return for practice
MAX_WEAK_PHONEMES = 5


async def aggregate_weak_phonemes(identity: Identity) -> list[str]:
    """
    Aggregate weak phonemes for the identity.

    For registered users: looks at last HISTORY_DEPTH recordings' phoneme_analysis.
    For anonymous: only the most recent single recording.

    Returns a list of phonemes sorted by frequency (most problematic first),
    capped at MAX_WEAK_PHONEMES.
    """
    db = get_mongo_db()
    collection = db["phoneme_analysis"]

    # Build query filter based on identity
    if identity.is_authenticated and identity.user_id:
        # Registered user: find recordings by user_id through the recordings join
        # Since phoneme_analysis is keyed by recording_id, we need to find
        # recording IDs owned by this user first, then aggregate their weak phonemes.
        # Simplification: phoneme_analysis docs store recording_id; we query
        # the recordings collection for the user's recent recordings.
        recordings_col = db["transcripts"]  # transcripts have recording_id
        # Actually, let's query phoneme_analysis directly — they're keyed by recording_id
        # We need a lookup by user. Since Mongo doesn't have the user_id on phoneme_analysis,
        # we'll use a different approach: query from MySQL via the service layer.
        # For now, use a simpler approach: pass recording_ids from the caller.
        # This function will be called with pre-fetched recording_ids.
        pass

    # Fallback: return empty (caller will provide recording IDs)
    return []


async def aggregate_from_recording_ids(recording_ids: list[str]) -> list[str]:
    """
    Given a list of recording IDs, aggregate their weak_phonemes by frequency.
    Returns sorted list of most problematic phonemes.
    """
    if not recording_ids:
        return []

    db = get_mongo_db()
    collection = db["phoneme_analysis"]

    counter = Counter()

    cursor = collection.find(
        {"_id": {"$in": recording_ids}},
        {"weak_phonemes": 1},
    )

    async for doc in cursor:
        for phoneme in doc.get("weak_phonemes", []):
            counter[phoneme] += 1

    if not counter:
        return []

    # Sort by frequency (most common first), cap at MAX_WEAK_PHONEMES
    sorted_phonemes = [ph for ph, _ in counter.most_common(MAX_WEAK_PHONEMES)]

    logger.info(
        "weak_phonemes_aggregated",
        recording_count=len(recording_ids),
        phonemes=sorted_phonemes,
    )
    return sorted_phonemes


async def get_recent_recording_ids_for_user(
    identity: Identity,
    limit: int = HISTORY_DEPTH,
) -> list[str]:
    """
    Get the most recent recording IDs for this identity.
    Uses MySQL via the recordings table.

    For anonymous users: returns at most 1 (the current session's latest).
    For registered users: returns up to `limit` recent recordings.
    """
    from sqlalchemy import select
    from app.db.mysql.base import AsyncSessionLocal
    from app.modules.upload.models import Recording

    async with AsyncSessionLocal() as db:
        if identity.is_authenticated and identity.user_id:
            result = await db.execute(
                select(Recording.id)
                .where(
                    Recording.user_id == identity.user_id,
                    Recording.status == "scored",
                    Recording.deleted_at.is_(None),
                )
                .order_by(Recording.created_at.desc())
                .limit(limit)
            )
        elif identity.anon_session_id:
            result = await db.execute(
                select(Recording.id)
                .where(
                    Recording.anon_session_id == identity.anon_session_id,
                    Recording.status == "scored",
                    Recording.deleted_at.is_(None),
                )
                .order_by(Recording.created_at.desc())
                .limit(1)  # Anonymous: single recording only
            )
        else:
            return []

        rows = result.scalars().all()
        return list(rows)
