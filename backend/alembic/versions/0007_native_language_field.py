"""add native_language to users table

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-31

Phase 28: Optional native language field for L1-adaptive scoring and feedback.
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("native_language", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "native_language")
