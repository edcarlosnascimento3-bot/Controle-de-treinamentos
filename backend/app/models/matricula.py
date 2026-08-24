from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Matricula(Base):
    """Registro de que um funcionário realizou um treinamento."""

    __tablename__ = "matriculas"

    id: Mapped[int] = mapped_column(primary_key=True)
    funcionario_id: Mapped[int] = mapped_column(
        ForeignKey("funcionarios.id", ondelete="CASCADE"), index=True
    )
    treinamento_id: Mapped[int] = mapped_column(
        ForeignKey("treinamentos.id", ondelete="CASCADE"), index=True
    )
    data_realizacao: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    data_validade: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    instrutor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    aprovado: Mapped[bool] = mapped_column(Boolean, default=True)
    tipo_avaliacao: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nota: Mapped[int | None] = mapped_column(nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    funcionario: Mapped["Funcionario"] = relationship(back_populates="matriculas")
    treinamento: Mapped["Treinamento"] = relationship(back_populates="matriculas")
    certificado: Mapped["Certificado | None"] = relationship(
        back_populates="matricula", uselist=False, cascade="all, delete-orphan", lazy="joined"
    )


class Certificado(Base):
    __tablename__ = "certificados"

    id: Mapped[int] = mapped_column(primary_key=True)
    matricula_id: Mapped[int] = mapped_column(
        ForeignKey("matriculas.id", ondelete="CASCADE"), unique=True
    )
    numero: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_emissao: Mapped[date] = mapped_column(Date, default=date.today)
    arquivo_nome: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    matricula: Mapped[Matricula] = relationship(back_populates="certificado")
