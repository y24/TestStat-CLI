"""add plan labels

Revision ID: 20260622_0016
Revises: 20260618_0015
Create Date: 2026-06-22 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260622_0016"
down_revision: Union[str, None] = "20260618_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plan_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("testing_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("testing_id", "label", name="uq_plan_labels_testing_label"),
    )
    op.create_index(op.f("ix_plan_labels_id"), "plan_labels", ["id"], unique=False)
    op.create_index(op.f("ix_plan_labels_testing_id"), "plan_labels", ["testing_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_plan_labels_testing_id"), table_name="plan_labels")
    op.drop_index(op.f("ix_plan_labels_id"), table_name="plan_labels")
    op.drop_table("plan_labels")
