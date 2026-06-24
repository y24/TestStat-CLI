"""add project azure bug settings

Revision ID: 20260624_0025
Revises: 20260624_0024
Create Date: 2026-06-24 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260624_0025"
down_revision: Union[str, None] = "20260624_0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("bug_parent_work_item_id", sa.Integer(), nullable=True))
    op.add_column("projects", sa.Column("bug_work_item_type", sa.String(length=255), nullable=True))
    op.add_column("projects", sa.Column("bug_tag", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "bug_tag")
    op.drop_column("projects", "bug_work_item_type")
    op.drop_column("projects", "bug_parent_work_item_id")
