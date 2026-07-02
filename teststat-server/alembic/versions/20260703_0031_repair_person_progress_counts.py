"""repair missing person progress count columns

Revision ID: 20260703_0031
Revises: 20260703_0030
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260703_0031"
down_revision: Union[str, None] = "20260703_0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Some existing databases were stamped at 0030 without receiving the columns.
    # IF NOT EXISTS also keeps this safe for databases where 0030 ran normally.
    op.execute("ALTER TABLE daily_person_progress ADD COLUMN IF NOT EXISTS completed INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE daily_person_progress ADD COLUMN IF NOT EXISTS executed INTEGER NOT NULL DEFAULT 0")
    op.execute("UPDATE daily_person_progress SET completed = count, executed = count WHERE completed = 0 AND executed = 0")


def downgrade() -> None:
    # 0030 owns these columns; downgrading only the repair must not remove them.
    pass