from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Gestor(Base):
    __tablename__ = "gestores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), index=True)
    cargo_id: Mapped[int | None] = mapped_column(ForeignKey("cargos.id"), nullable=True)
    foto: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    foto_tipo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cargo: Mapped["Cargo | None"] = relationship(back_populates="gestores", lazy="joined")
