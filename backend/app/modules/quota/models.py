"""
SQLAlchemy model for anonymous usage quota tracking.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mysql.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class AnonymousUsage(Base):
    __tablename__ = "anonymous_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # The signed cookie value identifies the anonymous session
    anon_session_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    # Soft device fingerprint — SHA-256(IP + User-Agent).  Not PII-grade, just a
    # secondary signal to raise the bar for quota bypass via cookie deletion.
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    analyses_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
