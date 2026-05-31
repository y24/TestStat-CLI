"""add progress status settings

Revision ID: 20260601_0006
Revises: 20260531_0005
Create Date: 2026-06-01 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260601_0006"
down_revision: Union[str, None] = "20260531_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "progress_status_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("normal_threshold", sa.Float(), nullable=False, server_default="90"),
        sa.Column("caution_threshold", sa.Float(), nullable=False, server_default="90"),
        sa.Column("warning_threshold", sa.Float(), nullable=False, server_default="60"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO progress_status_settings "
        "(id, normal_threshold, caution_threshold, warning_threshold) "
        "VALUES (1, 90, 90, 60)"
    )


def downgrade() -> None:
    op.drop_table("progress_status_settings")
