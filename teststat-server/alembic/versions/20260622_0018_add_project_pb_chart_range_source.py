"""add project pb chart range source

Revision ID: 20260622_0018
Revises: 20260622_0017
Create Date: 2026-06-22 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260622_0018"
down_revision: Union[str, None] = "20260622_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "pb_chart_range_source",
            sa.String(length=32),
            nullable=False,
            server_default="plan_actual",
        ),
    )
    op.alter_column("projects", "pb_chart_range_source", server_default=None)


def downgrade() -> None:
    op.drop_column("projects", "pb_chart_range_source")