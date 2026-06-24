"""add is_disabled to plan labels

Revision ID: 20260624_0024
Revises: 20260623_0023
Create Date: 2026-06-24 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260624_0024"
down_revision: Union[str, None] = "20260623_0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "plan_labels",
        sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("plan_labels", "is_disabled")
