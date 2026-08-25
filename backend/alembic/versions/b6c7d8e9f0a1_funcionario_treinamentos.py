"""treinamentos obrigatorios por funcionario

Revision ID: b6c7d8e9f0a1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa


revision = "b6c7d8e9f0a1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "funcionario_treinamentos",
        sa.Column(
            "funcionario_id",
            sa.Integer(),
            sa.ForeignKey("funcionarios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "treinamento_id",
            sa.Integer(),
            sa.ForeignKey("treinamentos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("funcionario_treinamentos")
