"""adicionar foto ao funcionario

Revision ID: c3d4e5f60718
Revises: 1a2b3c4d5e6f
Create Date: 2026-08-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f60718'
down_revision: str | None = '1a2b3c4d5e6f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("funcionarios", sa.Column("foto", sa.LargeBinary, nullable=True))
    op.add_column("funcionarios", sa.Column("foto_tipo", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("funcionarios", "foto_tipo")
    op.drop_column("funcionarios", "foto")
