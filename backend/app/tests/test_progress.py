"""
Tests for the progress/comparison module.

Testing checklist:
- First recording returns empty/onboarding state (no crash)
- Comparison math correct
- Only common phonemes in per_phoneme comparison
- History paginates correctly
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.progress.schemas import ComparisonResponse, ScoreDelta
from app.modules.progress.service import get_comparison, get_history


# ── Comparison tests ──────────────────────────────────────────────────────────

class TestComparison:
    @pytest.mark.asyncio
    async def test_first_recording_no_crash(self):
        """First recording returns has_previous=False, not an error."""
        from app.modules.scoring.models import Score
        from app.modules.upload.models import Recording

        db = AsyncMock()

        # Current score exists
        curr_score = Score(
            recording_id="r1",
            overall_score=75.0,
            fluency_score=70.0,
            accuracy_score=80.0,
        )
        score_result = MagicMock()
        score_result.scalar_one_or_none = MagicMock(return_value=curr_score)

        # Current recording
        curr_rec = Recording(
            id="r1", user_id="u1", status="scored",
            created_at=datetime.now(UTC),
            storage_path="x.wav", duration_seconds=30.0,
        )
        rec_result = MagicMock()
        rec_result.scalar_one_or_none = MagicMock(return_value=curr_rec)

        # No previous recording
        prev_result = MagicMock()
        prev_result.scalar_one_or_none = MagicMock(return_value=None)

        db.execute = AsyncMock(side_effect=[score_result, rec_result, prev_result])

        result = await get_comparison("r1", "u1", db)

        assert isinstance(result, ComparisonResponse)
        assert result.has_previous is False
        assert result.overall.curr == 75.0
        assert result.overall.prev is None
        assert result.overall.delta is None

    @pytest.mark.asyncio
    async def test_second_recording_shows_delta(self):
        """Second recording correctly computes deltas."""
        from app.modules.scoring.models import Score
        from app.modules.upload.models import Recording
        from app.modules.progress.models import PhonemeScore

        db = AsyncMock()

        # Current score
        curr_score = Score(
            recording_id="r2", overall_score=84.0,
            fluency_score=78.0, accuracy_score=90.0,
        )
        # Current recording
        curr_rec = Recording(
            id="r2", user_id="u1", status="scored",
            created_at=datetime.now(UTC),
            storage_path="x.wav", duration_seconds=30.0,
        )
        # Previous recording ID
        prev_id_result = MagicMock()
        prev_id_result.scalar_one_or_none = MagicMock(return_value="r1")

        # Previous score
        prev_score = Score(
            recording_id="r1", overall_score=76.0,
            fluency_score=72.0, accuracy_score=80.0,
        )

        # Phoneme scores for current
        curr_phonemes = [
            PhonemeScore(recording_id="r2", phoneme="θ", accuracy_score=88.0),
            PhonemeScore(recording_id="r2", phoneme="r", accuracy_score=75.0),
        ]
        # Phoneme scores for previous
        prev_phonemes = [
            PhonemeScore(recording_id="r1", phoneme="θ", accuracy_score=61.0),
            PhonemeScore(recording_id="r1", phoneme="r", accuracy_score=70.0),
            PhonemeScore(recording_id="r1", phoneme="v", accuracy_score=50.0),  # not in current
        ]

        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            idx = call_count[0]
            result = MagicMock()
            if idx == 1:  # curr score
                result.scalar_one_or_none = MagicMock(return_value=curr_score)
            elif idx == 2:  # curr recording
                result.scalar_one_or_none = MagicMock(return_value=curr_rec)
            elif idx == 3:  # prev recording id
                result.scalar_one_or_none = MagicMock(return_value="r1")
            elif idx == 4:  # prev score
                result.scalar_one_or_none = MagicMock(return_value=prev_score)
            elif idx == 5:  # curr phoneme scores
                result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=curr_phonemes)))
            elif idx == 6:  # prev phoneme scores
                result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=prev_phonemes)))
            return result

        db.execute = mock_execute

        result = await get_comparison("r2", "u1", db)

        assert result.has_previous is True
        assert result.overall.prev == 76.0
        assert result.overall.curr == 84.0
        assert result.overall.delta == 8.0
        assert result.accuracy.delta == 10.0

        # Only θ and r are in both — v is excluded
        phoneme_names = [p.phoneme for p in result.per_phoneme]
        assert "θ" in phoneme_names
        assert "r" in phoneme_names
        assert "v" not in phoneme_names  # not in current recording

        # Check θ delta
        theta = next(p for p in result.per_phoneme if p.phoneme == "θ")
        assert theta.prev == 61.0
        assert theta.curr == 88.0
        assert theta.delta == 27.0


# ── History tests ─────────────────────────────────────────────────────────────

class TestHistory:
    @pytest.mark.asyncio
    async def test_empty_history(self):
        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=0)
        scores_result = MagicMock()
        scores_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        db.execute = AsyncMock(side_effect=[count_result, scores_result])

        result = await get_history("u1", db)
        assert result.total == 0
        assert result.entries == []

    @pytest.mark.asyncio
    async def test_history_returns_entries(self):
        from app.modules.scoring.models import Score

        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=2)

        scores = [
            Score(recording_id="r2", overall_score=84.0, fluency_score=78.0,
                  accuracy_score=90.0, created_at=datetime.now(UTC)),
            Score(recording_id="r1", overall_score=76.0, fluency_score=72.0,
                  accuracy_score=80.0, created_at=datetime.now(UTC) - timedelta(days=1)),
        ]
        scores_result = MagicMock()
        scores_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=scores)))

        db.execute = AsyncMock(side_effect=[count_result, scores_result])

        result = await get_history("u1", db, limit=50, offset=0)
        assert result.total == 2
        assert len(result.entries) == 2
        assert result.entries[0].overall_score == 84.0
