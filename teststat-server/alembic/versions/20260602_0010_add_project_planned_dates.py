"""add project planned dates

Revision ID: 20260602_0010
Revises: 20260601_0009
Create Date: 2026-06-02 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260602_0010"
down_revision: Union[str, None] = "20260601_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("planned_start_date", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("planned_end_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "planned_end_date")
    op.drop_column("projects", "planned_start_date")
