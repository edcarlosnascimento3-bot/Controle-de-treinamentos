from datetime import datetime

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, func

from ..database import Base
from .enums import CategoriaTreinamento


class Treinamento(Base):
    __tablename__ = "treinamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(250), index=True)
    categoria: Mapped[CategoriaTreinamento] = mapped_column(
        String(20), default=CategoriaTreinamento.CORPORATIVO, index=True
    )
    norma: Mapped[str | None] = mapped_column(String(50), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    carga_horaria: Mapped[float | None] = mapped_column(Float, nullable=True)
    validade_meses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    integracao: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    matriculas: Mapped[list["Matricula"]] = relationship(
        back_populates="treinamento", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def categoria_label(self) -> str:
        if self.categoria == CategoriaTreinamento.NR:
            return "NR"
        if self.categoria == CategoriaTreinamento.CORPORATIVO:
            return "Corporativo"
        return self.categoria or "—"

    @property
    def validade_label(self) -> str:
        return f"{self.validade_meses} meses" if self.validade_meses else "Não expira"
