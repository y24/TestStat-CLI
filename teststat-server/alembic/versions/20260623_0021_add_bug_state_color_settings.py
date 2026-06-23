"""add bug state color settings

Revision ID: 20260623_0021
Revises: 20260623_0020
Create Date: 2026-06-23 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260623_0021"
down_revision: Union[str, None] = "20260623_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bug_state_color_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("state", sa.String(length=255), nullable=False),
        sa.Column("background_color", sa.String(length=7), nullable=False),
        sa.Column("text_color", sa.String(length=7), nullable=False),
        sa.Column("border_color", sa.String(length=7), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state"),
    )
    op.bulk_insert(
        sa.table(
            "bug_state_color_settings",
            sa.column("state", sa.String),
            sa.column("background_color", sa.String),
            sa.column("text_color", sa.String),
            sa.column("border_color", sa.String),
            sa.column("display_order", sa.Integer),
        ),
        [
            {
                "state": "New",
                "background_color": "#f7f9fb",
                "text_color": "#5f6b7a",
                "border_color": "#d8dee8",
                "display_order": 0,
            },
            {
                "state": "In Progress",
                "background_color": "#eef9ff",
                "text_color": "#0369a1",
                "border_color": "#bae6fd",
                "display_order": 1,
            },
            {
                "state": "Dev In Progress",
                "background_color": "#f5f0ff",
                "text_color": "#6b46c1",
                "border_color": "#ddd0ff",
                "display_order": 2,
            },
            {
                "state": "Resolved",
                "background_color": "#e9d5ff",
                "text_color": "#581c87",
                "border_color": "#c084fc",
                "display_order": 3,
            },
            {
                "state": "Done",
                "background_color": "#edf8f3",
                "text_color": "#147d54",
                "border_color": "#bfdacb",
                "display_order": 4,
            },
            {
                "state": "Suspend",
                "background_color": "#fff8e6",
                "text_color": "#8a5a00",
                "border_color": "#f5d58a",
                "display_order": 5,
            },
        ],
    )
    op.alter_column("bug_state_color_settings", "display_order", server_default=None)


def downgrade() -> None:
    op.drop_table("bug_state_color_settings")
