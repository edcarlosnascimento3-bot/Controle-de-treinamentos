"""Adiciona permissoes por pagina ao usuario

Revision ID: d5e6f7a8b9c0
Revises: a7c8d9e0f1a2
Create Date: 2026-08-23
"""

import sqlalchemy as sa
from alembic import op

revision = "d5e6f7a8b9c0"
down_revision = "a7c8d9e0f1a2"
branch_labels = None
depends_on = None

PADRAO_POR_PAPEL = {
    "admin": "painel,funcionarios,treinamentos,matriculas,relatorios,setores,cargos,gestores,categorias,kpis,usuarios,inativos",
    "rh": "painel,funcionarios,treinamentos,matriculas,relatorios,setores,cargos,gestores,categorias,kpis,inativos",
    "gestor": "painel,relatorios,setores,cargos,gestores,categorias,kpis",
    "colaborador": "painel",
    "visualizador": "matriculas",
}


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("permissoes", sa.String(length=500), nullable=True))

    for papel, permissoes in PADRAO_POR_PAPEL.items():
        op.execute(
            sa.text(
                "UPDATE users SET permissoes = :p WHERE role = :r AND permissoes IS NULL"
            ).bindparams(p=permissoes, r=papel)
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("permissoes")
