"""criar tabela categorias

Revision ID: 65bbc6ffa297
Revises: 8d3599902f84
Create Date: 2026-08-14 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65bbc6ffa297'
down_revision: Union[str, None] = '8d3599902f84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('categorias',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nome')
    )


def downgrade() -> None:
    op.drop_table('categorias')
