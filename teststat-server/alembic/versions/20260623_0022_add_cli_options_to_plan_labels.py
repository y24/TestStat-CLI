"""add cli options to plan labels

Revision ID: 20260623_0022
Revises: 20260623_0021
Create Date: 2026-06-23 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260623_0022"
down_revision: Union[str, None] = "20260623_0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("plan_labels", sa.Column("target_sheets", sa.JSON(), nullable=True))
    op.add_column("plan_labels", sa.Column("ignore_sheets", sa.JSON(), nullable=True))
    op.add_column("plan_labels", sa.Column("include_hidden_sheets", sa.Boolean(), nullable=True))
    op.add_column("plan_labels", sa.Column("target_environments", sa.JSON(), nullable=True))
    op.add_column("plan_labels", sa.Column("ignore_environments", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("plan_labels", "ignore_environments")
    op.drop_column("plan_labels", "target_environments")
    op.drop_column("plan_labels", "include_hidden_sheets")
    op.drop_column("plan_labels", "ignore_sheets")
    op.drop_column("plan_labels", "target_sheets")
