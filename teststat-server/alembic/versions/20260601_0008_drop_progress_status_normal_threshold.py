"""drop progress status normal threshold

Revision ID: 20260601_0008
Revises: 20260601_0007
Create Date: 2026-06-01 00:20:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260601_0008"
down_revision: Union[str, None] = "20260601_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("progress_status_settings", "normal_threshold")


def downgrade() -> None:
    op.add_column(
        "progress_status_settings",
        sa.Column("normal_threshold", sa.Float(), nullable=False, server_default="90"),
    )
    op.alter_column("progress_status_settings", "normal_threshold", server_default=None)
