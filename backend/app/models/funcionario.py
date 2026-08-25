from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Setor(Base):
    __tablename__ = "setores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    funcionarios: Mapped[list["Funcionario"]] = relationship(back_populates="setor")


class Cargo(Base):
    __tablename__ = "cargos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    funcionarios: Mapped[list["Funcionario"]] = relationship(back_populates="cargo")
    gestores: Mapped[list["Gestor"]] = relationship(back_populates="cargo")


class Funcionario(Base):
    __tablename__ = "funcionarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), index=True)
    cpf: Mapped[str | None] = mapped_column(String(14), unique=True, nullable=True)
    matricula: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    data_admissao: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_demissao: Mapped[date | None] = mapped_column(Date, nullable=True)
    turno: Mapped[str | None] = mapped_column(String(30), nullable=True)
    unidade: Mapped[str | None] = mapped_column(String(60), nullable=True)
    setor_id: Mapped[int | None] = mapped_column(ForeignKey("setores.id"), nullable=True)
    cargo_id: Mapped[int | None] = mapped_column(ForeignKey("cargos.id"), nullable=True)
    foto: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    foto_tipo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    setor: Mapped[Setor | None] = relationship(back_populates="funcionarios", lazy="joined")
    cargo: Mapped[Cargo | None] = relationship(back_populates="funcionarios", lazy="joined")
    treinamentos_obrigatorios: Mapped[list["Treinamento"]] = relationship(
        "Treinamento",
        secondary="funcionario_treinamentos",
        lazy="selectin",
    )
    matriculas: Mapped[list["Matricula"]] = relationship(
        back_populates="funcionario", cascade="all, delete-orphan", lazy="selectin"
    )
    usuario: Mapped["User | None"] = relationship(back_populates="funcionario")

    @property
    def admissao_str(self) -> str:
        return self.data_admissao.isoformat() if self.data_admissao else ""

    @property
    def ativo_label(self) -> str:
        return "Ativo" if self.ativo else "Inativo"
