"""initial schema

Revision ID: 20260531_0001
Revises:
Create Date: 2026-05-31 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260531_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "testings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("testing_id", sa.Integer(), nullable=False),
        sa.Column("project_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("testing_id"),
    )
    op.create_index(op.f("ix_testings_id"), "testings", ["id"], unique=False)
    op.create_index(op.f("ix_testings_testing_id"), "testings", ["testing_id"], unique=False)

    op.create_table(
        "file_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("testing_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("environment", sa.String(length=255), nullable=True),
        sa.Column("total_cases", sa.Integer(), nullable=False),
        sa.Column("available_cases", sa.Integer(), nullable=False),
        sa.Column("excluded_cases", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Integer(), nullable=False),
        sa.Column("executed", sa.Integer(), nullable=False),
        sa.Column("not_run", sa.Integer(), nullable=False),
        sa.Column("completed_rate", sa.Float(), nullable=False),
        sa.Column("executed_rate", sa.Float(), nullable=False),
        sa.Column("result_pass", sa.Integer(), nullable=False),
        sa.Column("result_fixed", sa.Integer(), nullable=False),
        sa.Column("result_fail", sa.Integer(), nullable=False),
        sa.Column("result_blocked", sa.Integer(), nullable=False),
        sa.Column("result_suspend", sa.Integer(), nullable=False),
        sa.Column("result_na", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("latest_update", sa.Date(), nullable=True),
        sa.Column("sender", sa.String(length=255), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["testing_id"], ["testings.testing_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_file_progress_id"), "file_progress", ["id"], unique=False)
    op.create_index(op.f("ix_file_progress_testing_id"), "file_progress", ["testing_id"], unique=False)

    op.create_table(
        "daily_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("testing_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("environment", sa.String(length=255), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("result_pass", sa.Integer(), nullable=False),
        sa.Column("result_fixed", sa.Integer(), nullable=False),
        sa.Column("result_fail", sa.Integer(), nullable=False),
        sa.Column("result_blocked", sa.Integer(), nullable=False),
        sa.Column("result_suspend", sa.Integer(), nullable=False),
        sa.Column("result_na", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Integer(), nullable=False),
        sa.Column("executed", sa.Integer(), nullable=False),
        sa.Column("planned", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["testing_id"], ["testings.testing_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_daily_progress_date"), "daily_progress", ["date"], unique=False)
    op.create_index(op.f("ix_daily_progress_id"), "daily_progress", ["id"], unique=False)
    op.create_index(op.f("ix_daily_progress_testing_id"), "daily_progress", ["testing_id"], unique=False)

    op.create_table(
        "daily_person_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("testing_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("environment", sa.String(length=255), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("person", sa.String(length=255), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["testing_id"], ["testings.testing_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_daily_person_progress_date"), "daily_person_progress", ["date"], unique=False)
    op.create_index(op.f("ix_daily_person_progress_id"), "daily_person_progress", ["id"], unique=False)
    op.create_index(op.f("ix_daily_person_progress_testing_id"), "daily_person_progress", ["testing_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_daily_person_progress_testing_id"), table_name="daily_person_progress")
    op.drop_index(op.f("ix_daily_person_progress_id"), table_name="daily_person_progress")
    op.drop_index(op.f("ix_daily_person_progress_date"), table_name="daily_person_progress")
    op.drop_table("daily_person_progress")
    op.drop_index(op.f("ix_daily_progress_testing_id"), table_name="daily_progress")
    op.drop_index(op.f("ix_daily_progress_id"), table_name="daily_progress")
    op.drop_index(op.f("ix_daily_progress_date"), table_name="daily_progress")
    op.drop_table("daily_progress")
    op.drop_index(op.f("ix_file_progress_testing_id"), table_name="file_progress")
    op.drop_index(op.f("ix_file_progress_id"), table_name="file_progress")
    op.drop_table("file_progress")
    op.drop_index(op.f("ix_testings_testing_id"), table_name="testings")
    op.drop_index(op.f("ix_testings_id"), table_name="testings")
    op.drop_table("testings")
