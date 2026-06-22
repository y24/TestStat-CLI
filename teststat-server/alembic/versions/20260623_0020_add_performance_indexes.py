"""add performance indexes

Revision ID: 20260623_0020
Revises: 20260622_0019
Create Date: 2026-06-23 00:00:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260623_0020"
down_revision: Union[str, None] = "20260622_0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_daily_progress_testing_label_date",
        "daily_progress",
        ["testing_id", "label", "date"],
        unique=False,
    )
    op.create_index(
        "ix_file_progress_testing_label",
        "file_progress",
        ["testing_id", "label"],
        unique=False,
    )
    op.create_index(
        "ix_plans_testing_label_active",
        "plans",
        ["testing_id", "label", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_plan_daily_plan_date",
        "plan_daily",
        ["plan_id", "date"],
        unique=False,
    )
    op.create_index(
        "ix_test_result_bug_snapshots_testing_label_date",
        "test_result_bug_snapshots",
        ["testing_id", "label", "snapshot_date"],
        unique=False,
    )
    op.create_index(
        "ix_bug_snapshots_testing_created",
        "bug_snapshots",
        ["testing_id", "created_date"],
        unique=False,
    )
    op.create_index(
        "ix_bug_snapshots_testing_finish",
        "bug_snapshots",
        ["testing_id", "finish_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bug_snapshots_testing_finish", table_name="bug_snapshots")
    op.drop_index("ix_bug_snapshots_testing_created", table_name="bug_snapshots")
    op.drop_index(
        "ix_test_result_bug_snapshots_testing_label_date",
        table_name="test_result_bug_snapshots",
    )
    op.drop_index("ix_plan_daily_plan_date", table_name="plan_daily")
    op.drop_index("ix_plans_testing_label_active", table_name="plans")
    op.drop_index("ix_file_progress_testing_label", table_name="file_progress")
    op.drop_index("ix_daily_progress_testing_label_date", table_name="daily_progress")
