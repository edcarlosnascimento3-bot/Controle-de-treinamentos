"""flag integracao no treinamento (regra segue o treinamento, nao o nome)

Revision ID: a7c8d9e0f1a2
Revises: f8a1b2c3d4e5
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "a7c8d9e0f1a2"
down_revision = "f8a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("treinamentos") as batch:
        batch.add_column(
            sa.Column("integracao", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    op.execute(
        "UPDATE treinamentos SET integracao = TRUE WHERE lower(nome) = 'integração das áreas'"
    )


def downgrade() -> None:
    with op.batch_alter_table("treinamentos") as batch:
        batch.drop_column("integracao")
