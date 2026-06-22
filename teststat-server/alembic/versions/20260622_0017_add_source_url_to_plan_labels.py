"""add source url to plan labels

Revision ID: 20260622_0017
Revises: 20260622_0016
Create Date: 2026-06-22 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260622_0017"
down_revision: Union[str, None] = "20260622_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("plan_labels", sa.Column("source_url", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("plan_labels", "source_url")
