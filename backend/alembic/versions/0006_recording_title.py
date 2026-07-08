"""add title column to recordings

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-08 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recordings", sa.Column("title", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("recordings", "title")
