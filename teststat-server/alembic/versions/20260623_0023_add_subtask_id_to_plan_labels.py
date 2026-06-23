"""add subtask_id to plan labels

Revision ID: 20260623_0023
Revises: 20260623_0022
Create Date: 2026-06-23 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260623_0023"
down_revision: Union[str, None] = "20260623_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("plan_labels", sa.Column("subtask_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("plan_labels", "subtask_id")
