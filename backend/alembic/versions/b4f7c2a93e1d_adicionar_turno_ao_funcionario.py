"""adicionar turno ao funcionario

Revision ID: b4f7c2a93e1d
Revises: 65bbc6ffa297
Create Date: 2026-08-15 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4f7c2a93e1d'
down_revision: str | None = '65bbc6ffa297'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("funcionarios", sa.Column("turno", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("funcionarios", "turno")
