from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Table, func

from ..database import Base


funcionario_treinamento = Table(
    "funcionario_treinamentos",
    Base.metadata,
    Column(
        "funcionario_id",
        ForeignKey("funcionarios.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "treinamento_id",
        ForeignKey("treinamentos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("created_at", DateTime, server_default=func.now()),
)
