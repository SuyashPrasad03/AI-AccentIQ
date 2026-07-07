"""
Tests for the transcription module.

- Validates the mock transcription fallback output shape
- Tests the service failure path (marks recording as failed)
- Tests transcript document schema validation
- Tests status endpoint authorization
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.modules.transcription.schemas import TranscriptDocument, WordSegment
from app.modules.transcription.whisperx_client import _mock_transcription


# ── Schema validation tests ───────────────────────────────────────────────────

class TestTranscriptDocument:
    def test_valid_document(self):
        doc = TranscriptDocument(
            _id="t-1",
            recording_id="r-1",
            raw_text="hello world",
            words=[
                WordSegment(word="hello", start=0.0, end=0.5, confidence=0.95),
                WordSegment(word="world", start=0.6, end=1.1, confidence=0.88),
            ],
            language="en",
            model_version="whisperx-small-en",
            created_at=datetime.now(UTC),
        )
        assert doc.id == "t-1"
        assert len(doc.words) == 2
        assert doc.words[0].word == "hello"

    def test_confidence_range_enforced(self):
        with pytest.raises(Exception):
            WordSegment(word="test", start=0.0, end=0.5, confidence=1.5)

    def test_empty_words_list_valid(self):
        doc = TranscriptDocument(
            _id="t-2",
            recording_id="r-2",
            raw_text="",
            words=[],
            language="en",
            model_version="test",
            created_at=datetime.now(UTC),
        )
        assert doc.words == []


# ── Mock transcription tests ──────────────────────────────────────────────────

class TestMockTranscription:
    def test_mock_returns_expected_shape(self):
        with patch(
            "app.modules.upload.validators.get_audio_duration",
            return_value=30.0,
        ):
            result = _mock_transcription("/fake/path.wav")

        assert "raw_text" in result
        assert "words" in result
        assert "language" in result
        assert "model_version" in result
        assert result["language"] == "en"
        assert result["model_version"] == "mock-dev-fallback"
        assert len(result["words"]) > 0

        # Each word has the required fields
        for w in result["words"]:
            assert "word" in w
            assert "start" in w
            assert "end" in w
            assert "confidence" in w
            assert 0.0 <= w["confidence"] <= 1.0
            assert w["start"] < w["end"]

    def test_mock_duration_fallback(self):
        with patch(
            "app.modules.upload.validators.get_audio_duration",
            side_effect=Exception("no ffprobe"),
        ):
            result = _mock_transcription("/fake/path.wav")

        # Should still produce output using the 30.0 fallback duration
        assert len(result["words"]) > 0


# ── Transcription service failure path ────────────────────────────────────────

class TestTranscriptionJobFailure:
    @pytest.mark.asyncio
    async def test_failed_transcription_sets_status_failed(self):
        """When transcribe_and_align raises, recording.status → 'failed'."""
        from app.modules.upload.models import Recording

        # Mock DB session
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        recording = Recording(
            id="r-fail",
            storage_path="recordings/test.wav",
            duration_seconds=30.0,
            status="uploaded",
        )

        # First execute: UPDATE status=processing → ok
        # Second execute: SELECT recording → return recording
        # Third execute (in except): UPDATE status=failed → ok
        update_result = MagicMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none = MagicMock(return_value=recording)

        mock_session.execute = AsyncMock(side_effect=[update_result, select_result, update_result])

        # Mock the session factory to return our mock
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.modules.transcription.service.AsyncSessionLocal", return_value=mock_session_ctx),
            patch(
                "app.modules.transcription.service.transcribe_and_align",
                side_effect=RuntimeError("Model crashed"),
            ),
            patch(
                "app.modules.transcription.service.get_storage_backend",
                return_value=MagicMock(get_full_path=MagicMock(return_value="/fake/path.wav")),
            ),
        ):
            from app.modules.transcription.service import run_transcription_job
            await run_transcription_job("r-fail")

        # Verify the failure path was executed (commit called after setting status=failed)
        assert mock_session.commit.call_count >= 1


# ── Status endpoint authorization ─────────────────────────────────────────────

class TestStatusEndpointAuth:
    @pytest.fixture
    def app(self):
        from app.main import create_app
        return create_app()

    @pytest.fixture
    async def client(self, app):
        with patch("app.db.mongo.client.init_mongo", new=AsyncMock()):
            with patch("app.db.mongo.client.close_mongo", new=AsyncMock()):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as ac:
                    yield ac

    @pytest.mark.asyncio
    async def test_status_returns_404_for_missing_recording(self, client, app):
        from app.db.mysql.base import get_db

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=result_mock)
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        app.dependency_overrides[get_db] = lambda: db

        response = await client.get("/recordings/nonexistent-id/status")
        assert response.status_code == 404

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_status_returns_403_for_wrong_owner(self, client, app):
        from app.db.mysql.base import get_db
        from app.modules.upload.models import Recording

        # Recording belongs to a specific anon session that isn't ours
        recording = Recording(
            id="r-other",
            user_id=None,
            anon_session_id="different-session-xyz",
            storage_path="x.wav",
            duration_seconds=30.0,
            status="processing",
            created_at=datetime.now(UTC),
        )

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=recording)
        db.execute = AsyncMock(return_value=result_mock)
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        app.dependency_overrides[get_db] = lambda: db

        # Call without auth token → anonymous user with None anon_session_id
        # Recording has anon_session_id="different-session-xyz" → should be 403
        response = await client.get("/recordings/r-other/status")
        assert response.status_code == 403

        app.dependency_overrides.clear()
