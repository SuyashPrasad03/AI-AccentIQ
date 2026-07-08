"""
SQLAlchemy model for audio recordings.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Either user_id (registered) or anon_session_id (anonymous) identifies the owner
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    anon_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Relative path within the storage backend (never absolute, never user-controlled)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)

    # User-editable name for this recording
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Duration of the original upload in seconds (from ffprobe)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)

    # Processing status lifecycle: uploaded → processing → scored | failed
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uploaded"
    )

    # Optional: pointer to the MongoDB transcript document (set in Phase 4)
    mongo_transcript_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Soft-delete for DPDP compliance (Phase 10 enforces)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
