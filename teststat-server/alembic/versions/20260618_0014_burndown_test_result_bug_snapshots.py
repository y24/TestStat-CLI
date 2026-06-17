"""burndown test result bug snapshots (fail_count -> detected_count)

Revision ID: 20260618_0014
Revises: 20260618_0013
Create Date: 2026-06-18 03:00:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260618_0014"
down_revision: Union[str, None] = "20260618_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # fail_count（その日の Fail 件数）→ detected_count（その日の検出増分）に意味変更。
    op.alter_column("test_result_bug_snapshots", "fail_count", new_column_name="detected_count")
    # 旧データは意味が異なるため、現在の daily_progress から再構築する（取込1回分のベースライン）。
    # detected_count = その日に検出された不具合数 = Fail + Suspend + Fixed。
    op.execute("DELETE FROM test_result_bug_snapshots")
    op.execute(
        """
        INSERT INTO test_result_bug_snapshots (
            testing_id,
            snapshot_date,
            detected_count,
            suspend_count,
            fixed_count,
            sent_at
        )
        SELECT
            dp.testing_id,
            dp.date,
            SUM(dp.result_fail + dp.result_suspend + dp.result_fixed),
            SUM(dp.result_suspend),
            SUM(dp.result_fixed),
            COALESCE(MAX(fp.sent_at), CURRENT_TIMESTAMP)
        FROM daily_progress dp
        LEFT JOIN file_progress fp ON fp.testing_id = dp.testing_id
        GROUP BY dp.testing_id, dp.date
        HAVING SUM(dp.result_fail + dp.result_suspend + dp.result_fixed) > 0
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM test_result_bug_snapshots")
    op.alter_column("test_result_bug_snapshots", "detected_count", new_column_name="fail_count")
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
