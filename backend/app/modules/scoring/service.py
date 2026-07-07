"""
Scoring service — triggered automatically after transcription completes.

Pipeline: transcription done → score_recording_job → MySQL scores + Mongo phoneme_analysis → status=scored
"""

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.mongo.phoneme_analysis import insert_phoneme_analysis, get_phoneme_analysis
from app.db.mongo.transcripts import get_transcript_by_recording_id
from app.db.mysql.base import AsyncSessionLocal
from app.modules.scoring.formula import score_recording
from app.modules.scoring.models import Score
from app.modules.scoring.schemas import ScoreResponse, WordScoreOut
from app.modules.upload.models import Recording

logger = get_logger(__name__)


async def run_scoring_job(recording_id: str) -> None:
    """
    Background job: score a recording after transcription.
    Reads transcript from Mongo, computes scores, stores results in both
    MySQL (summary) and Mongo (full word-level breakdown).
    """
    logger.info("scoring_job_start", recording_id=recording_id)

    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch transcript from Mongo
            transcript = await get_transcript_by_recording_id(recording_id)
            if transcript is None:
                logger.error("scoring_no_transcript", recording_id=recording_id)
                await _set_failed(db, recording_id)
                return

            # 2. Run scoring formula
            words_data = [
                {
                    "word": w.word,
                    "start": w.start,
                    "end": w.end,
                    "confidence": w.confidence,
                }
                for w in transcript.words
            ]

            # Compute total duration from the last word's end time
            total_duration = max(
                (w.end for w in transcript.words), default=30.0
            )

            result = score_recording(words_data, total_duration)

            # 3. Store full analysis in Mongo
            await insert_phoneme_analysis(
                recording_id=recording_id,
                word_scores=result["word_scores"],
                weak_phonemes=result["weak_phonemes"],
                overall_score=result["overall_score"],
                accuracy_score=result["accuracy_score"],
                fluency_score=result["fluency_score"],
            )

            # 4. Store summary in MySQL
            score_record = Score(
                recording_id=recording_id,
                overall_score=result["overall_score"],
                fluency_score=result["fluency_score"],
                accuracy_score=result["accuracy_score"],
            )
            db.add(score_record)

            # 5. Update recording status → scored
            await db.execute(
                update(Recording)
                .where(Recording.id == recording_id)
                .values(status="scored")
            )
            await db.commit()

            logger.info(
                "scoring_job_done",
                recording_id=recording_id,
                overall=result["overall_score"],
                accuracy=result["accuracy_score"],
                fluency=result["fluency_score"],
                weak_phonemes=result["weak_phonemes"],
            )

        except Exception as exc:
            logger.error(
                "scoring_job_failed",
                recording_id=recording_id,
                error=str(exc),
                exc_info=True,
            )
            await db.rollback()
            await _set_failed(db, recording_id)


async def get_score_for_recording(recording_id: str) -> ScoreResponse | None:
    """Fetch the full score (from Mongo) for API response."""
    analysis = await get_phoneme_analysis(recording_id)
    if analysis is None:
        return None

    word_scores = [
        WordScoreOut(
            word=w["word"],
            word_score=w["word_score"],
            detected_issue=w["detected_issue"],
            expected_phonemes=w["expected_phonemes"],
            substituted_as=w["substituted_as"],
            confidence=w["confidence"],
        )
        for w in analysis.get("words", [])
    ]

    return ScoreResponse(
        recording_id=recording_id,
        overall_score=analysis["overall_score"],
        accuracy_score=analysis["accuracy_score"],
        fluency_score=analysis["fluency_score"],
        word_scores=word_scores,
        weak_phonemes=analysis.get("weak_phonemes", []),
    )


async def _set_failed(db: AsyncSession, recording_id: str) -> None:
    try:
        await db.execute(
            update(Recording)
            .where(Recording.id == recording_id)
            .values(status="failed")
        )
        await db.commit()
    except Exception:
        pass
