"""add project bug axis max

Revision ID: 20260625_0028
Revises: 20260624_0027
Create Date: 2026-06-25 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260625_0028"
down_revision: Union[str, None] = "20260624_0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("bug_axis_max", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "bug_axis_max")
