"""add project bug count source

Revision ID: 20260618_0012
Revises: 20260602_0011
Create Date: 2026-06-18 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260618_0012"
down_revision: Union[str, None] = "20260602_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "bug_count_source",
            sa.String(length=32),
            nullable=False,
            server_default="azure_devops",
        ),
    )
    op.alter_column("projects", "bug_count_source", server_default=None)
    op.create_table(
        "test_result_bug_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("testing_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("fail_count", sa.Integer(), nullable=False),
        sa.Column("suspend_count", sa.Integer(), nullable=False),
        sa.Column("fixed_count", sa.Integer(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["testing_id"], ["testings.testing_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("testing_id", "snapshot_date", name="uq_test_result_bug_snapshots_testing_date"),
    )
    op.create_index("ix_test_result_bug_snapshots_id", "test_result_bug_snapshots", ["id"])
    op.create_index("ix_test_result_bug_snapshots_snapshot_date", "test_result_bug_snapshots", ["snapshot_date"])
    op.create_index("ix_test_result_bug_snapshots_testing_id", "test_result_bug_snapshots", ["testing_id"])
    op.execute(
        """
        INSERT INTO test_result_bug_snapshots (
            testing_id,
            snapshot_date,
            fail_count,
            suspend_count,
            fixed_count,
            sent_at
        )
        SELECT
            testing_id,
            date,
            SUM(result_fail),
            SUM(result_suspend),
            SUM(result_fixed),
            CURRENT_TIMESTAMP
        FROM daily_progress
        GROUP BY testing_id, date
        """
    )


def downgrade() -> None:
    op.drop_index("ix_test_result_bug_snapshots_testing_id", table_name="test_result_bug_snapshots")
    op.drop_index("ix_test_result_bug_snapshots_snapshot_date", table_name="test_result_bug_snapshots")
    op.drop_index("ix_test_result_bug_snapshots_id", table_name="test_result_bug_snapshots")
    op.drop_table("test_result_bug_snapshots")
    op.drop_column("projects", "bug_count_source")
