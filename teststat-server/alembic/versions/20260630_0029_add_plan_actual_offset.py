"""add plan actual offset setting

Revision ID: 20260630_0029
Revises: 20260625_0028
Create Date: 2026-06-30 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260630_0029"
down_revision: Union[str, None] = "20260625_0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "plan_labels",
        sa.Column("use_plan_as_actual_offset", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("plan_labels", "use_plan_as_actual_offset")
