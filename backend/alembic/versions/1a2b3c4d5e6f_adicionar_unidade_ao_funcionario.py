"""adicionar unidade ao funcionario

Revision ID: 1a2b3c4d5e6f
Revises: b4f7c2a93e1d
Create Date: 2026-08-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: str | None = 'b4f7c2a93e1d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("funcionarios", sa.Column("unidade", sa.String(60), nullable=True))


def downgrade() -> None:
    op.drop_column("funcionarios", "unidade")
