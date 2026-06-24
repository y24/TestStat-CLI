"""drop file_progress sender column

Revision ID: 20260624_0026
Revises: 20260624_0025
Create Date: 2026-06-24 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260624_0026"
down_revision: Union[str, None] = "20260624_0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("file_progress", "sender")


def downgrade() -> None:
    op.add_column("file_progress", sa.Column("sender", sa.String(length=255), nullable=True))
