"""add completed and executed person progress counts

Revision ID: 20260703_0030
Revises: 20260630_0029
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260703_0030"
down_revision: Union[str, None] = "20260630_0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("daily_person_progress", sa.Column("completed", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("daily_person_progress", sa.Column("executed", sa.Integer(), nullable=False, server_default="0"))
    op.execute("UPDATE daily_person_progress SET completed = count, executed = count")


def downgrade() -> None:
    op.drop_column("daily_person_progress", "executed")
    op.drop_column("daily_person_progress", "completed")