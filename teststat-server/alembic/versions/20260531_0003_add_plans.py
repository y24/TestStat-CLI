"""add plans and plan_daily tables

Revision ID: 20260531_0003
Revises: 20260531_0002
Create Date: 2026-05-31 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260531_0003"
down_revision: Union[str, None] = "20260531_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("testing_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("planned_total_cases", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plans_id"), "plans", ["id"], unique=False)
    op.create_index(op.f("ix_plans_testing_id"), "plans", ["testing_id"], unique=False)

    op.create_table(
        "plan_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("planned_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plan_daily_id"), "plan_daily", ["id"], unique=False)
    op.create_index(op.f("ix_plan_daily_plan_id"), "plan_daily", ["plan_id"], unique=False)
    op.create_index(op.f("ix_plan_daily_date"), "plan_daily", ["date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_plan_daily_date"), table_name="plan_daily")
    op.drop_index(op.f("ix_plan_daily_plan_id"), table_name="plan_daily")
    op.drop_index(op.f("ix_plan_daily_id"), table_name="plan_daily")
    op.drop_table("plan_daily")
    op.drop_index(op.f("ix_plans_testing_id"), table_name="plans")
    op.drop_index(op.f("ix_plans_id"), table_name="plans")
    op.drop_table("plans")
