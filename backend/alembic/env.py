import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# Garante que o pacote `app` seja importável a partir da raiz do backend.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database import Base
from app import models  # noqa: F401  # registra todas as tabelas no metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

DATABASE_URL = settings.DATABASE_URL

# No SQLite, o diretório pai do arquivo precisa existir antes de conectar.
if DATABASE_URL.startswith("sqlite:///") and DATABASE_URL != "sqlite:///:memory:":
    db_path = Path(DATABASE_URL.replace("sqlite:///", "", 1))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
