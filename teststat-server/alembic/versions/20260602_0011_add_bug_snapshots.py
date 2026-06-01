"""add bug snapshots

Revision ID: 20260602_0011
Revises: 20260602_0010
Create Date: 2026-06-02 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260602_0011"
down_revision: Union[str, None] = "20260602_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bug_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("testing_id", sa.Integer(), nullable=False),
        sa.Column("bug_work_item_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("state", sa.String(length=255), nullable=True),
        sa.Column("created_date", sa.Date(), nullable=True),
        sa.Column("finish_date", sa.Date(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["testing_id"], ["projects.testing_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bug_snapshots_id", "bug_snapshots", ["id"])
    op.create_index("ix_bug_snapshots_testing_id", "bug_snapshots", ["testing_id"])


def downgrade() -> None:
    op.drop_index("ix_bug_snapshots_testing_id", table_name="bug_snapshots")
    op.drop_index("ix_bug_snapshots_id", table_name="bug_snapshots")
    op.drop_table("bug_snapshots")
