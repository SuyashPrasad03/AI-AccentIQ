"""
SQLAlchemy model for DPDP consent audit trail.
Every explicit consent action is logged here — never deleted, only soft-referenced.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ConsentEvent(Base):
    __tablename__ = "consent_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Either user_id (registered) or anon_session_id (anonymous) must be set.
    # Both may be set if a user registers mid-session.
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    anon_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # What was consented to:
    #   "audio_processing"   — user allows their audio to be analysed
    #   "data_retention"     — user accepts the retention period
    #   "privacy_policy"     — user accepts the policy as a whole
    consent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DataDeletionRequest(Base):
    """Auditable record of every account deletion request (DPDP requirement)."""
    __tablename__ = "data_deletion_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
