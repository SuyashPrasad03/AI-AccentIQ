"""recordings table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-08 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recordings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("anon_session_id", sa.String(255), nullable=True),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
        sa.Column("mongo_transcript_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_recordings_user_id", "recordings", ["user_id"])
    op.create_index("ix_recordings_anon_session", "recordings", ["anon_session_id"])
    op.create_index("ix_recordings_status", "recordings", ["status"])


def downgrade() -> None:
    op.drop_table("recordings")
