from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_pagina, require_roles
from ..models import Pagina, Role, User
from ..templating import render

PERM = require_roles(Role.ADMIN, Role.RH)


def criar_router(*, model, prefix: str, singular: str, plural: str, maxlen: int, contar_usos, pagina: Pagina):
    """Cria um router CRUD simples (nome único) para setores, cargos e categorias.

    contar_usos(db, item) -> int  (quantos registros usam o item; bloqueia exclusão).
    pagina: página do menu que controla o acesso a este cadastro.
    """
    router = APIRouter(prefix=prefix, tags=[plural.lower()])
    url_base = prefix
    PAG = require_pagina(pagina)

    @router.get("", response_class=HTMLResponse)
    def listar(
        request: Request,
        user: User = Depends(PAG),
        db: Session = Depends(get_db),
    ):
        itens = db.query(model).order_by(model.nome).all()
        usos = {i.id: contar_usos(db, i) for i in itens}
        return render(
            request,
            "cadastros/list.html",
            {
                "user": user,
                "itens": itens,
                "usos": usos,
                "titulo": plural,
                "singular": singular,
                "url_base": url_base,
                "pode_editar": user.role in (Role.ADMIN, Role.RH),
            },
        )

    @router.get("/novo", response_class=HTMLResponse, dependencies=[Depends(PAG)])
    def novo(request: Request, user: User = Depends(PERM)):
        return render(
            request,
            "cadastros/form.html",
            {
                "user": user,
                "item": None,
                "titulo": f"Novo {singular.lower()}",
                "url_base": url_base,
                "acao": url_base,
                "maxlen": maxlen,
            },
        )

    @router.post("", dependencies=[Depends(PAG)])
    def criar(
        request: Request,
        nome: str = Form(""),
        user: User = Depends(PERM),
        db: Session = Depends(get_db),
    ):
        nome = nome.strip()
        if not nome:
            return RedirectResponse(f"{url_base}/novo?erro=" + quote("Informe o nome."), status_code=303)
        if db.query(model).filter(func.lower(model.nome) == nome.lower()).first():
            return RedirectResponse(f"{url_base}/novo?erro=" + quote(f"{singular} já cadastrado."), status_code=303)

        db.add(model(nome=nome))
        db.commit()
        return RedirectResponse(f"{url_base}?ok=" + quote(f"{singular} cadastrado."), status_code=303)

    @router.get("/{item_id}/editar", response_class=HTMLResponse, dependencies=[Depends(PAG)])
    def editar(
        item_id: int,
        request: Request,
        user: User = Depends(PERM),
        db: Session = Depends(get_db),
    ):
        item = db.get(model, item_id)
        if not item:
            raise HTTPException(404, f"{singular} não encontrado.")
        return render(
            request,
            "cadastros/form.html",
            {
                "user": user,
                "item": item,
                "titulo": f"Editar {singular.lower()}",
                "url_base": url_base,
                "acao": f"{url_base}/{item_id}/editar",
                "maxlen": maxlen,
            },
        )

    @router.post("/{item_id}/editar", dependencies=[Depends(PAG)])
    def atualizar(
        item_id: int,
        request: Request,
        nome: str = Form(""),
        user: User = Depends(PERM),
        db: Session = Depends(get_db),
    ):
        item = db.get(model, item_id)
        if not item:
            raise HTTPException(404, f"{singular} não encontrado.")

        nome = nome.strip()
        if not nome:
            return RedirectResponse(f"{url_base}/{item_id}/editar?erro=" + quote("Informe o nome."), status_code=303)
        dup = db.query(model).filter(func.lower(model.nome) == nome.lower(), model.id != item_id).first()
        if dup:
            return RedirectResponse(f"{url_base}/{item_id}/editar?erro=" + quote(f"{singular} já cadastrado."), status_code=303)

        item.nome = nome
        db.commit()
        return RedirectResponse(f"{url_base}?ok=" + quote("Dados atualizados."), status_code=303)

    @router.post("/{item_id}/excluir", dependencies=[Depends(PAG)])
    def excluir(
        item_id: int,
        request: Request,
        user: User = Depends(PERM),
        db: Session = Depends(get_db),
    ):
        item = db.get(model, item_id)
        if not item:
            raise HTTPException(404, f"{singular} não encontrado.")
        if contar_usos(db, item) > 0:
            return RedirectResponse(f"{url_base}?erro=" + quote(f"{singular} está em uso e não pode ser excluído."), status_code=303)
        db.delete(item)
        db.commit()
        return RedirectResponse(f"{url_base}?ok=" + quote(f"{singular} excluído."), status_code=303)

    return router
