"""test result bug snapshots per label

Revision ID: 20260618_0015
Revises: 20260618_0014
Create Date: 2026-06-18 06:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260618_0015"
down_revision: Union[str, None] = "20260618_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # テスト別（label 別）に不具合バーンダウンを保持できるよう label 列と制約を追加。
    op.add_column("test_result_bug_snapshots", sa.Column("label", sa.String(length=255), nullable=True))
    op.drop_constraint(
        "uq_test_result_bug_snapshots_testing_date", "test_result_bug_snapshots", type_="unique"
    )
    op.create_unique_constraint(
        "uq_test_result_bug_snapshots_testing_label_date",
        "test_result_bug_snapshots",
        ["testing_id", "label", "snapshot_date"],
    )

    # 旧データは label 合算のため再現できない。現在の daily_progress から label 別に再構築する。
    # detected_count = その日に検出された不具合数 = Fail + Suspend + Fixed（取込1回分のベースライン）。
    op.execute("DELETE FROM test_result_bug_snapshots")
    op.execute(
        """
        INSERT INTO test_result_bug_snapshots (
            testing_id,
            label,
            snapshot_date,
            detected_count,
            suspend_count,
            fixed_count,
            sent_at
        )
        SELECT
            dp.testing_id,
            dp.label,
            dp.date,
            SUM(dp.result_fail + dp.result_suspend + dp.result_fixed),
            SUM(dp.result_suspend),
            SUM(dp.result_fixed),
            COALESCE(
                (SELECT MAX(fp.sent_at) FROM file_progress fp WHERE fp.testing_id = dp.testing_id),
                CURRENT_TIMESTAMP
            )
        FROM daily_progress dp
        GROUP BY dp.testing_id, dp.label, dp.date
        HAVING SUM(dp.result_fail + dp.result_suspend + dp.result_fixed) > 0
        """
    )


def downgrade() -> None:
    # label を合算した状態に戻す。
    op.execute("DELETE FROM test_result_bug_snapshots")
    op.drop_constraint(
        "uq_test_result_bug_snapshots_testing_label_date", "test_result_bug_snapshots", type_="unique"
    )
    op.drop_column("test_result_bug_snapshots", "label")
    op.create_unique_constraint(
        "uq_test_result_bug_snapshots_testing_date",
        "test_result_bug_snapshots",
        ["testing_id", "snapshot_date"],
    )
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
            COALESCE(
                (SELECT MAX(fp.sent_at) FROM file_progress fp WHERE fp.testing_id = dp.testing_id),
                CURRENT_TIMESTAMP
            )
        FROM daily_progress dp
        GROUP BY dp.testing_id, dp.date
        HAVING SUM(dp.result_fail + dp.result_suspend + dp.result_fixed) > 0
        """
    )
