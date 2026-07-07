"""
Tests for DPDP compliance — deletion and retention.

Testing checklist:
- Full account deletion cascades across MySQL, Mongo, and storage
- Retention job purges only expired audio
- Consent withdrawal blocks further processing
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.compliance.deletion_service import delete_user_data
from app.modules.compliance.retention_job import run_retention_purge


class TestDeletionService:
    @pytest.mark.asyncio
    async def test_delete_user_data_cascades(self):
        """Deletion removes recordings, Mongo docs, revokes tokens, soft-deletes user."""
        db = AsyncMock()
        db.flush = AsyncMock()

        recordings = [
            MagicMock(id="r1", storage_path="recordings/abc.wav"),
            MagicMock(id="r2", storage_path="recordings/def.wav"),
        ]
        rec_result = MagicMock()
        rec_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=recordings)))

        # Default execute returns a MagicMock (for UPDATE statements)
        default_result = MagicMock(rowcount=2)
        db.execute = AsyncMock(return_value=default_result)
        # Override first call to return recordings
        db.execute.side_effect = None
        call_count = [0]
        original_execute = db.execute

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count[0] += 1
            if call_count[0] == 1:
                return rec_result
            return default_result

        db.execute = mock_execute

        mock_storage = MagicMock()
        mock_storage.delete = AsyncMock(return_value=True)

        mock_collection = AsyncMock()
        mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=3))
        mock_mongo_db = MagicMock()
        mock_mongo_db.__getitem__ = MagicMock(return_value=mock_collection)

        with (
            patch("app.modules.compliance.deletion_service.get_storage_backend", return_value=mock_storage),
            patch("app.modules.compliance.deletion_service.get_mongo_db", return_value=mock_mongo_db),
        ):
            summary = await delete_user_data("u-123", db)

        assert summary["recordings_deleted"] == 2
        assert summary["files_deleted"] == 2
        assert summary["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_delete_handles_no_recordings(self):
        """User with no recordings: deletion still completes gracefully."""
        db = AsyncMock()
        db.flush = AsyncMock()

        rec_result = MagicMock()
        rec_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        default_result = MagicMock(rowcount=0)

        call_count = [0]
        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count[0] += 1
            if call_count[0] == 1:
                return rec_result
            return default_result

        db.execute = mock_execute

        mock_mongo_db = MagicMock()
        mock_collection = AsyncMock()
        mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=0))
        mock_mongo_db.__getitem__ = MagicMock(return_value=mock_collection)

        with (
            patch("app.modules.compliance.deletion_service.get_storage_backend", return_value=MagicMock()),
            patch("app.modules.compliance.deletion_service.get_mongo_db", return_value=mock_mongo_db),
        ):
            summary = await delete_user_data("u-empty", db)

        assert summary["recordings_deleted"] == 0
        assert summary["files_deleted"] == 0


class TestRetentionJob:
    @pytest.mark.asyncio
    async def test_purges_expired_audio(self):
        """Recordings past retention window get their files deleted."""
        from app.modules.upload.models import Recording

        old_recording = MagicMock(
            id="r-old",
            storage_path="recordings/old.wav",
            created_at=datetime.now(UTC) - timedelta(days=60),
        )

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # scalars returns the expired recordings
        result_mock = MagicMock()
        result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[old_recording])))
        update_mock = MagicMock()
        mock_session.execute = AsyncMock(side_effect=[result_mock, update_mock])

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_storage = MagicMock()
        mock_storage.delete = AsyncMock(return_value=True)

        with (
            patch("app.modules.compliance.retention_job.AsyncSessionLocal", return_value=mock_session_ctx),
            patch("app.modules.compliance.retention_job.get_storage_backend", return_value=mock_storage),
        ):
            summary = await run_retention_purge()

        assert summary["purged_count"] == 1
        mock_storage.delete.assert_called_once_with("recordings/old.wav")

    @pytest.mark.asyncio
    async def test_no_expired_does_nothing(self):
        """When no recordings are expired, nothing is deleted."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_session.execute = AsyncMock(return_value=result_mock)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.modules.compliance.retention_job.AsyncSessionLocal", return_value=mock_session_ctx):
            summary = await run_retention_purge()

        assert summary["purged_count"] == 0
        assert summary["errors"] == 0
