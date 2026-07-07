"""phoneme_scores table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-08 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "phoneme_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recording_id",
            sa.String(36),
            sa.ForeignKey("recordings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phoneme", sa.String(10), nullable=False),
        sa.Column("accuracy_score", sa.Float, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_phoneme_scores_recording", "phoneme_scores", ["recording_id"])
    op.create_index(
        "ix_phoneme_scores_rec_phoneme",
        "phoneme_scores",
        ["recording_id", "phoneme"],
    )


def downgrade() -> None:
    op.drop_table("phoneme_scores")
