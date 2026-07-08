"""
Progress service — comparison and history logic.

Comparison: N vs N-1 (most recent vs immediately prior recording).
Only for registered users (anonymous get single-score view).
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.progress.models import PhonemeScore
from app.modules.progress.schemas import (
    ComparisonResponse,
    HistoryEntry,
    HistoryResponse,
    PhonemeComparison,
    ScoreDelta,
)
from app.modules.scoring.models import Score
from app.modules.upload.models import Recording

logger = get_logger(__name__)


async def get_comparison(
    recording_id: str,
    user_id: str,
    db: AsyncSession,
) -> ComparisonResponse:
    """
    Compare the given recording's scores against the user's immediately prior recording.
    Returns deltas for overall, fluency, accuracy, and per-phoneme.
    """
    # Get current recording's score
    curr_score = await _get_score(recording_id, db)
    if curr_score is None:
        return _empty_comparison(recording_id)

    # Get the previous recording (by created_at, before the current one)
    curr_recording = await db.execute(
        select(Recording).where(Recording.id == recording_id)
    )
    curr_rec = curr_recording.scalar_one_or_none()
    if curr_rec is None:
        return _empty_comparison(recording_id)

    # Find the immediately preceding scored recording for this user
    prev_result = await db.execute(
        select(Recording.id)
        .where(
            Recording.user_id == user_id,
            Recording.status == "scored",
            Recording.deleted_at.is_(None),
            Recording.created_at < curr_rec.created_at,
        )
        .order_by(Recording.created_at.desc())
        .limit(1)
    )
    prev_id = prev_result.scalar_one_or_none()

    if prev_id is None:
        # First recording — no comparison available
        return ComparisonResponse(
            recording_id=recording_id,
            has_previous=False,
            overall=ScoreDelta(prev=None, curr=curr_score.overall_score, delta=None),
            fluency=ScoreDelta(prev=None, curr=curr_score.fluency_score, delta=None),
            accuracy=ScoreDelta(prev=None, curr=curr_score.accuracy_score, delta=None),
            per_phoneme=[],
        )

    prev_score = await _get_score(prev_id, db)
    if prev_score is None:
        return _empty_comparison(recording_id)

    # Per-phoneme comparison
    curr_phonemes = await _get_phoneme_scores(recording_id, db)
    prev_phonemes = await _get_phoneme_scores(prev_id, db)

    # Only compare phonemes present in BOTH recordings
    common_phonemes = set(curr_phonemes.keys()) & set(prev_phonemes.keys())
    per_phoneme = [
        PhonemeComparison(
            phoneme=ph,
            prev=prev_phonemes[ph],
            curr=curr_phonemes[ph],
            delta=round(curr_phonemes[ph] - prev_phonemes[ph], 1),
        )
        for ph in sorted(common_phonemes)
    ]

    return ComparisonResponse(
        recording_id=recording_id,
        has_previous=True,
        overall=ScoreDelta(
            prev=prev_score.overall_score,
            curr=curr_score.overall_score,
            delta=round(curr_score.overall_score - prev_score.overall_score, 1),
        ),
        fluency=ScoreDelta(
            prev=prev_score.fluency_score,
            curr=curr_score.fluency_score,
            delta=round(curr_score.fluency_score - prev_score.fluency_score, 1),
        ),
        accuracy=ScoreDelta(
            prev=prev_score.accuracy_score,
            curr=curr_score.accuracy_score,
            delta=round(curr_score.accuracy_score - prev_score.accuracy_score, 1),
        ),
        per_phoneme=per_phoneme,
    )


async def get_history(
    user_id: str,
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> HistoryResponse:
    """
    Return the user's full score timeline (paginated).
    Most recent first.
    """
    # Count total
    count_result = await db.execute(
        select(func.count())
        .select_from(Score)
        .join(Recording, Score.recording_id == Recording.id)
        .where(
            Recording.user_id == user_id,
            Recording.deleted_at.is_(None),
        )
    )
    total = count_result.scalar() or 0

    # Fetch page
    result = await db.execute(
        select(Score, Recording.title)
        .join(Recording, Score.recording_id == Recording.id)
        .where(
            Recording.user_id == user_id,
            Recording.deleted_at.is_(None),
        )
        .order_by(Score.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()

    entries = [
        HistoryEntry(
            recording_id=score.recording_id,
            title=title,
            overall_score=score.overall_score,
            fluency_score=score.fluency_score,
            accuracy_score=score.accuracy_score,
            created_at=score.created_at,
        )
        for score, title in rows
    ]

    return HistoryResponse(entries=entries, total=total)


# ── Private helpers ───────────────────────────────────────────────────────────

async def _get_score(recording_id: str, db: AsyncSession) -> Score | None:
    result = await db.execute(
        select(Score).where(Score.recording_id == recording_id)
    )
    return result.scalar_one_or_none()


async def _get_phoneme_scores(recording_id: str, db: AsyncSession) -> dict[str, float]:
    """Return {phoneme: accuracy_score} for a recording."""
    result = await db.execute(
        select(PhonemeScore).where(PhonemeScore.recording_id == recording_id)
    )
    rows = result.scalars().all()
    return {r.phoneme: r.accuracy_score for r in rows}


def _empty_comparison(recording_id: str) -> ComparisonResponse:
    return ComparisonResponse(
        recording_id=recording_id,
        has_previous=False,
        overall=ScoreDelta(prev=None, curr=0.0, delta=None),
        fluency=ScoreDelta(prev=None, curr=0.0, delta=None),
        accuracy=ScoreDelta(prev=None, curr=0.0, delta=None),
        per_phoneme=[],
    )
