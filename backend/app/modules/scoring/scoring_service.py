"""
Scoring service — orchestrates the full scoring pipeline.

Pipeline: transcription done → score_recording_job → MySQL scores + Mongo phoneme_analysis → status=scored

Phase 24 changes:
  - Supports two scoring engines via SCORING_ENGINE env flag: "gop" or "legacy"
  - When SCORING_ENGINE=gop: runs the GOP pipeline (wav2vec2-CTC posteriors)
  - When SCORING_ENGINE=legacy: runs the original confidence-proxy scorer
  - Both engines always log their scores for comparison during transition
  - The "active" engine's scores are stored as the official result
  - Both results are logged side-by-side for every request
"""

from pathlib import Path

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.settings import settings
from app.db.mongo.phoneme_analysis import insert_phoneme_analysis, get_phoneme_analysis
from app.db.mysql.base import AsyncSessionLocal
from app.modules.scoring.schemas import ScoreResponse, WordScoreOut
from app.modules.scoring.models import Score
from app.modules.upload.models import Recording
from app.modules.progress.models import PhonemeScore

logger = get_logger(__name__)


def _get_scoring_engine() -> str:
    """Get the active scoring engine from settings."""
    return getattr(settings, "scoring_engine", "legacy")


async def run_scoring_job(recording_id: str) -> None:
    """
    Background job: score a recording after transcription.
    Runs both engines and logs comparison, but stores only the active engine's result.
    """
    from app.db.mongo.transcripts import get_transcript_by_recording_id

    logger.info("scoring_job_start", recording_id=recording_id)

    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch transcript from Mongo
            transcript = await get_transcript_by_recording_id(recording_id)
            if transcript is None:
                logger.error("scoring_no_transcript", recording_id=recording_id)
                await _set_failed(db, recording_id)
                return

            # 2. Prepare word data
            words_data = [
                {
                    "word": w.word,
                    "start": w.start,
                    "end": w.end,
                    "confidence": w.confidence,
                }
                for w in transcript.words
            ]

            total_duration = max(
                (w.end for w in transcript.words), default=30.0
            )

            # 3. Get the recording's audio path for GOP scoring
            from sqlalchemy import select
            rec_result = await db.execute(
                select(Recording).where(Recording.id == recording_id)
            )
            recording = rec_result.scalar_one_or_none()
            audio_path = None
            if recording:
                from app.modules.upload.storage.local_disk import get_storage_backend
                storage = get_storage_backend()
                audio_path = storage.get_full_path(recording.storage_path)

            # 4. Run scoring engines
            active_engine = _get_scoring_engine()
            legacy_result = None
            gop_result = None

            # Always run legacy for comparison logging
            legacy_result = _run_legacy_scoring(words_data, total_duration)

            # Try GOP if enabled and audio is available
            if audio_path and Path(audio_path).exists():
                gop_result = _run_gop_scoring(audio_path, words_data, total_duration)

            # 5. Determine which result to store
            if active_engine == "gop" and gop_result is not None:
                result = gop_result
                engine_used = "gop"
            else:
                result = legacy_result
                engine_used = "legacy"

            # 6. Log side-by-side comparison
            _log_comparison(recording_id, legacy_result, gop_result, engine_used)

            # 6b. Enrich with error classification (Phase 25)
            if engine_used == "gop" and gop_result and audio_path:
                result = _enrich_with_error_types(result, audio_path)

            # 7. Store full analysis in Mongo (with engine metadata)
            await insert_phoneme_analysis(
                recording_id=recording_id,
                word_scores=result["word_scores"],
                weak_phonemes=result["weak_phonemes"],
                overall_score=result["overall_score"],
                accuracy_score=result["accuracy_score"],
                fluency_score=result["fluency_score"],
                scoring_engine_version=engine_used,
                gop_raw_scores=result.get("gop_raw_scores"),
                gop_confidence=result.get("gop_confidence"),
            )

            # 8. Store summary in MySQL
            score_record = Score(
                recording_id=recording_id,
                overall_score=result["overall_score"],
                fluency_score=result["fluency_score"],
                accuracy_score=result["accuracy_score"],
            )
            db.add(score_record)

            # 8b. Store per-phoneme scores for progress
            await _store_phoneme_scores(db, recording_id, result["word_scores"])

            # 9. Update recording status → scored
            await db.execute(
                update(Recording)
                .where(Recording.id == recording_id)
                .values(status="scored")
            )
            await db.commit()

            logger.info(
                "scoring_job_done",
                recording_id=recording_id,
                engine=engine_used,
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


def _run_legacy_scoring(words_data: list[dict], total_duration: float) -> dict:
    """Run the legacy confidence-proxy scoring engine."""
    from app.modules.scoring.legacy_diff_scorer import score_recording_legacy
    return score_recording_legacy(words_data, total_duration)


def _enrich_with_error_types(result: dict, audio_path: str) -> dict:
    """
    Enrich GOP scoring results with error-type classification (Phase 25).
    Falls back gracefully if the classifier is unavailable.
    """
    try:
        from app.modules.scoring.error_classifier.model import predict_single, is_model_available

        if not is_model_available():
            # Try loading
            from app.modules.scoring.error_classifier.model import _ensure_model_loaded
            if not _ensure_model_loaded():
                return result

        gop_raw_scores = result.get("gop_raw_scores", [])
        word_scores = result.get("word_scores", [])

        for word_idx, (raw, ws) in enumerate(zip(gop_raw_scores, word_scores)):
            phonemes_data = raw.get("phonemes", [])
            phoneme_error_types = []

            for ph_data in phonemes_data:
                prediction = predict_single(
                    gop_score=ph_data.get("gop_score", -5.0),
                    gop_gap=ph_data.get("gap", 3.0),
                    duration=0.08,  # approximate, fine for classification
                    duration_ratio=1.0,
                    energy_mean=0.01,
                )
                phoneme_error_types.append(prediction)

            # Add error types to word score
            if phoneme_error_types:
                # Word-level error type: most severe error among its phonemes
                error_priority = {"substitution": 4, "deletion": 3, "insertion": 2, "distortion": 1, "correct": 0}
                worst_error = max(phoneme_error_types, key=lambda x: error_priority.get(x["error_type"], 0))
                ws["error_type"] = worst_error["error_type"]
                ws["error_type_confidence"] = worst_error["error_type_confidence"]
                ws["phoneme_error_types"] = phoneme_error_types

        logger.info("error_classification_done", words_classified=len(word_scores))
        return result

    except Exception as exc:
        logger.warning("error_classification_failed", error=str(exc))
        return result


def _run_gop_scoring(
    audio_path: str,
    words_data: list[dict],
    total_duration: float,
) -> dict | None:
    """
    Run the GOP scoring engine. Returns None if model isn't available.
    """
    try:
        from app.modules.scoring.phoneme_recognizer import (
            get_frame_log_probs,
            load_audio_for_gop,
        )
        from app.modules.scoring.gop_engine import compute_gop_scores
        from app.modules.scoring.score_normalizer import (
            normalize_word_scores,
            compute_overall_scores,
        )
        from app.modules.scoring.phoneme_compare import get_reference_phonemes

        # 1. Load audio
        audio_array, sample_rate = load_audio_for_gop(audio_path)

        # 2. Get frame-level log-probs from wav2vec2-CTC
        recognition_result = get_frame_log_probs(audio_array, sample_rate)

        # 3. Get reference phonemes for each word
        reference_phonemes_per_word = [
            get_reference_phonemes(w["word"]) for w in words_data
        ]

        # 4. Compute GOP scores
        word_gop_results = compute_gop_scores(
            recognition_result, words_data, reference_phonemes_per_word
        )

        # 5. Normalize to 0-100 scale
        normalized_word_scores = normalize_word_scores(word_gop_results)

        # 6. Compute overall scores
        overall_scores = compute_overall_scores(
            normalized_word_scores, words_data, total_duration
        )

        # 7. Build raw GOP data for MongoDB storage
        gop_raw_scores = []
        for wgr in word_gop_results:
            gop_raw_scores.append({
                "word": wgr.word,
                "word_gop_score": wgr.word_gop_score,
                "phonemes": [
                    {
                        "phoneme": ps.phoneme,
                        "gop_score": ps.gop_score,
                        "max_posterior_phoneme": ps.max_posterior_phoneme,
                        "max_posterior_score": ps.max_posterior_score,
                        "gap": ps.gap,
                    }
                    for ps in wgr.phoneme_scores
                ],
            })

        # Compute GOP confidence: mean of all word GOP scores (raw)
        gop_confidence = 0.0
        if word_gop_results:
            import numpy as np
            gop_confidence = float(np.mean([w.word_gop_score for w in word_gop_results]))

        return {
            "overall_score": overall_scores["overall_score"],
            "accuracy_score": overall_scores["accuracy_score"],
            "fluency_score": overall_scores["fluency_score"],
            "word_scores": normalized_word_scores,
            "weak_phonemes": overall_scores["weak_phonemes"],
            "gop_raw_scores": gop_raw_scores,
            "gop_confidence": round(gop_confidence, 4),
        }

    except Exception as exc:
        logger.error(
            "gop_scoring_failed",
            audio_path=audio_path,
            error=str(exc),
            exc_info=True,
        )
        return None


def _log_comparison(
    recording_id: str,
    legacy_result: dict | None,
    gop_result: dict | None,
    active_engine: str,
) -> None:
    """Log side-by-side comparison of both engines for transition analysis."""
    legacy_overall = legacy_result["overall_score"] if legacy_result else None
    legacy_accuracy = legacy_result["accuracy_score"] if legacy_result else None
    gop_overall = gop_result["overall_score"] if gop_result else None
    gop_accuracy = gop_result["accuracy_score"] if gop_result else None

    logger.info(
        "scoring_engine_comparison",
        recording_id=recording_id,
        active_engine=active_engine,
        legacy_overall=legacy_overall,
        legacy_accuracy=legacy_accuracy,
        gop_overall=gop_overall,
        gop_accuracy=gop_accuracy,
        delta_overall=(
            round(gop_overall - legacy_overall, 1)
            if gop_overall is not None and legacy_overall is not None
            else None
        ),
        delta_accuracy=(
            round(gop_accuracy - legacy_accuracy, 1)
            if gop_accuracy is not None and legacy_accuracy is not None
            else None
        ),
    )

    # Log per-word comparison for the first 5 words (keep logs manageable)
    if legacy_result and gop_result:
        legacy_words = legacy_result.get("word_scores", [])[:5]
        gop_words = gop_result.get("word_scores", [])[:5]

        for i, (lw, gw) in enumerate(zip(legacy_words, gop_words)):
            logger.info(
                "scoring_word_comparison",
                recording_id=recording_id,
                word=lw.get("word", ""),
                legacy_score=lw.get("word_score"),
                legacy_issue=lw.get("detected_issue"),
                gop_score=gw.get("word_score"),
                gop_issue=gw.get("detected_issue"),
            )


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


async def _store_phoneme_scores(
    db: AsyncSession, recording_id: str, word_scores: list[dict]
) -> None:
    """
    Aggregate per-phoneme accuracy from word scores and store in phoneme_scores table.
    """
    from collections import defaultdict

    phoneme_totals = defaultdict(list)

    for ws in word_scores:
        for phoneme in ws.get("expected_phonemes", []):
            phoneme_totals[phoneme].append(ws["word_score"])

    for phoneme, scores in phoneme_totals.items():
        avg_score = sum(scores) / len(scores) if scores else 0.0
        record = PhonemeScore(
            recording_id=recording_id,
            phoneme=phoneme,
            accuracy_score=round(avg_score, 1),
        )
        db.add(record)
