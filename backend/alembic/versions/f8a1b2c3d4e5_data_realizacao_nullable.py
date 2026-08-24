"""data_realizacao passa a aceitar nulo (registro pendente de realização)

Revision ID: f8a1b2c3d4e5
Revises: 913fd74ebbda
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "f8a1b2c3d4e5"
down_revision = "913fd74ebbda"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("matriculas") as batch:
        batch.alter_column(
            "data_realizacao",
            existing_type=sa.Date(),
            nullable=True,
        )


def downgrade() -> None:
    op.execute("DELETE FROM matriculas WHERE data_realizacao IS NULL")
    with op.batch_alter_table("matriculas") as batch:
        batch.alter_column(
            "data_realizacao",
            existing_type=sa.Date(),
            nullable=False,
        )
