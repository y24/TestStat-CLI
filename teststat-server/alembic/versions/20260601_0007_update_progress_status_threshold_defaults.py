"""update progress status threshold defaults

Revision ID: 20260601_0007
Revises: 20260601_0006
Create Date: 2026-06-01 00:10:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260601_0007"
down_revision: Union[str, None] = "20260601_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE progress_status_settings ALTER COLUMN caution_threshold SET DEFAULT 90")
    op.execute("ALTER TABLE progress_status_settings ALTER COLUMN warning_threshold SET DEFAULT 60")
    op.execute(
        "UPDATE progress_status_settings "
        "SET caution_threshold = 90, warning_threshold = 60 "
        "WHERE id = 1 "
        "AND normal_threshold = 90 "
        "AND caution_threshold = 70 "
        "AND warning_threshold = 50"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE progress_status_settings ALTER COLUMN caution_threshold SET DEFAULT 70")
    op.execute("ALTER TABLE progress_status_settings ALTER COLUMN warning_threshold SET DEFAULT 50")
    op.execute(
        "UPDATE progress_status_settings "
        "SET caution_threshold = 70, warning_threshold = 50 "
        "WHERE id = 1 "
        "AND normal_threshold = 90 "
        "AND caution_threshold = 90 "
        "AND warning_threshold = 60"
    )
