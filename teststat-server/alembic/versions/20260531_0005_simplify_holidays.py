"""simplify holidays table

Revision ID: 20260531_0005
Revises: 20260531_0004
Create Date: 2026-05-31 18:45:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260531_0005"
down_revision: Union[str, None] = "20260531_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("holidays")
    }
    if "updated_at" in existing_columns:
        op.drop_column("holidays", "updated_at")
    if "source" in existing_columns:
        op.drop_column("holidays", "source")
    op.execute("DELETE FROM holidays WHERE date < '2025-01-01'")


def downgrade() -> None:
    op.add_column(
        "holidays",
        sa.Column("source", sa.String(length=255), nullable=False, server_default="cao"),
    )
    op.add_column(
        "holidays",
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.alter_column("holidays", "source", server_default=None)
