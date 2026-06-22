"""add pb chart settings

Revision ID: 20260622_0019
Revises: 20260622_0018
Create Date: 2026-06-22 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260622_0019"
down_revision: Union[str, None] = "20260622_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pb_chart_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bug_axis_max", sa.Integer(), nullable=False, server_default="30"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("INSERT INTO pb_chart_settings (id, bug_axis_max) VALUES (1, 30)")
    op.alter_column("pb_chart_settings", "bug_axis_max", server_default=None)


def downgrade() -> None:
    op.drop_table("pb_chart_settings")
