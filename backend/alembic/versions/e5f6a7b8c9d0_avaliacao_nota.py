"""avaliacao: tipo_avaliacao e nota na matricula

Revision ID: e5f6a7b8c9d0
Revises: d5e6f7a8b9c0
Create Date: 2026-08-24
"""

import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("matriculas") as batch:
        batch.add_column(sa.Column("tipo_avaliacao", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("nota", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("matriculas") as batch:
        batch.drop_column("nota")
        batch.drop_column("tipo_avaliacao")
