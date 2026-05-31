"""add holidays table

Revision ID: 20260531_0004
Revises: 20260531_0003
Create Date: 2026-05-31 18:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260531_0004"
down_revision: Union[str, None] = "20260531_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "holidays",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("date"),
    )
    op.create_index(op.f("ix_holidays_date"), "holidays", ["date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_holidays_date"), table_name="holidays")
    op.drop_table("holidays")
