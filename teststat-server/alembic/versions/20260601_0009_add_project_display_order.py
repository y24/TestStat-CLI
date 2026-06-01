"""add project display order

Revision ID: 20260601_0009
Revises: 20260601_0008
Create Date: 2026-06-01 01:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260601_0009"
down_revision: Union[str, None] = "20260601_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("display_order", sa.Integer(), nullable=True))
    bind = op.get_bind()
    project_ids = bind.execute(sa.text("select id from projects order by archived, updated_at desc, id")).scalars().all()
    for index, project_id in enumerate(project_ids):
        bind.execute(
            sa.text("update projects set display_order = :display_order where id = :id"),
            {"display_order": index, "id": project_id},
        )
    op.alter_column("projects", "display_order", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.drop_column("projects", "display_order")
