"""rebuild test result bug snapshots from daily progress

Revision ID: 20260618_0013
Revises: 20260618_0012
Create Date: 2026-06-18 00:00:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260618_0013"
down_revision: Union[str, None] = "20260618_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM test_result_bug_snapshots")
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
            dp.testing_id,
            dp.date,
            SUM(dp.result_fail),
            SUM(dp.result_suspend),
            SUM(dp.result_fixed),
            COALESCE(MAX(fp.sent_at), CURRENT_TIMESTAMP)
        FROM daily_progress dp
        LEFT JOIN file_progress fp ON fp.testing_id = dp.testing_id
        GROUP BY dp.testing_id, dp.date
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM test_result_bug_snapshots")
