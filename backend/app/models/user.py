from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .enums import MENU_LATERAL, PAGINA_LABELS, PAGINA_SOMENTE_ADMIN, Pagina, ROLE_LABELS, Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    nome: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(String(20), default=Role.COLABORADOR)
    permissoes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    funcionario_id: Mapped[int | None] = mapped_column(
        ForeignKey("funcionarios.id", ondelete="SET NULL"), nullable=True
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    funcionario: Mapped["Funcionario | None"] = relationship(
        back_populates="usuario", lazy="joined"
    )

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(Role(self.role), self.role)

    @property
    def eh_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def lista_permissoes(self) -> set[str]:
        if self.eh_admin:
            return {p.value for p in PAGINA_LABELS}
        return {p.strip() for p in (self.permissoes or "").split(",") if p.strip()}

    def pode_acessar(self, chave: str | Pagina) -> bool:
        valor = chave.value if isinstance(chave, Pagina) else str(chave)
        return valor in self.lista_permissoes

    @property
    def menu_itens(self) -> list[dict]:
        """Itens do menu lateral que o usuário pode visualizar."""
        itens: list[dict] = []
        for item in MENU_LATERAL:
            pagina: Pagina = item["pagina"]
            if pagina in PAGINA_SOMENTE_ADMIN and not self.eh_admin:
                continue
            if not self.pode_acessar(pagina):
                continue
            itens.append(
                {
                    "rotulo": PAGINA_LABELS[pagina],
                    "url": item["url"],
                    "prefixo": item["prefixo"],
                    "exato": item.get("exato", False),
                    "excecao": item.get("excecao"),
                }
            )
        return itens

    @property
    def primeira_pagina_url(self) -> str | None:
        """URL da primeira página do menu que o usuário pode acessar."""
        itens = self.menu_itens
        return itens[0]["url"] if itens else None
