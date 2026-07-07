"""
SQLAlchemy model for per-phoneme scores (normalized summary table).
Populated at scoring time; enables fast SQL comparisons without Mongo re-scans.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class PhonemeScore(Base):
    __tablename__ = "phoneme_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    recording_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recordings.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    phoneme: Mapped[str] = mapped_column(String(10), nullable=False)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
