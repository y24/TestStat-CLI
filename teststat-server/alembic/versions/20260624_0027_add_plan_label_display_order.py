"""add plan label display order

Revision ID: 20260624_0027
Revises: 20260624_0026
Create Date: 2026-06-24 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260624_0027"
down_revision: Union[str, None] = "20260624_0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("plan_labels", sa.Column("display_order", sa.Integer(), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("select id, testing_id from plan_labels order by testing_id, label, id")
    ).all()
    index_by_testing_id: dict[int, int] = {}
    for row in rows:
        index = index_by_testing_id.get(row.testing_id, 0)
        bind.execute(
            sa.text("update plan_labels set display_order = :display_order where id = :id"),
            {"display_order": index, "id": row.id},
        )
        index_by_testing_id[row.testing_id] = index + 1
    op.alter_column("plan_labels", "display_order", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.drop_column("plan_labels", "display_order")
