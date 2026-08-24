from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_pagina, require_roles
from ..models import Cargo, Gestor, Pagina, Role, User
from ..templating import render
from ._helpers import ler_foto

router = APIRouter(prefix="/gestores", tags=["gestores"])

PERM = require_roles(Role.ADMIN, Role.RH)
PAG = require_pagina(Pagina.GESTORES)


def _limpar(value: str | None) -> str | None:
    v = (value or "").strip()
    return v or None


def _select_cargo(db: Session, cargo_id: int | None, novo_cargo: str | None) -> int | None:
    nome = _limpar(novo_cargo)
    if nome:
        from sqlalchemy import func

        c = db.query(Cargo).filter(func.lower(Cargo.nome) == nome.lower()).first()
        if not c:
            c = Cargo(nome=nome)
            db.add(c)
            db.flush()
        return c.id
    return cargo_id


@router.get("", response_class=HTMLResponse)
def listar(
    request: Request,
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
):
    gestores = db.query(Gestor).order_by(Gestor.nome).all()
    return render(
        request,
        "gestores/list.html",
        {
            "user": user,
            "gestores": gestores,
            "pode_editar": user.role in (Role.ADMIN, Role.RH),
        },
    )


@router.get("/novo", response_class=HTMLResponse, dependencies=[Depends(PAG)])
def novo(
    request: Request,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    return render(
        request,
        "gestores/form.html",
        {
            "user": user,
            "gestor": None,
            "cargos": db.query(Cargo).order_by(Cargo.nome).all(),
        },
    )


@router.post("", dependencies=[Depends(PAG)])
def criar(
    request: Request,
    nome: str = Form(...),
    cargo_id: int | None = Form(None),
    novo_cargo: str = Form(""),
    foto: UploadFile | None = File(None),
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    nome = _limpar(nome)
    if not nome:
        return RedirectResponse("/gestores/novo?erro=" + quote("Informe o nome."), status_code=303)

    conteudo_foto, tipo_foto, erro_foto = ler_foto(foto)
    if erro_foto:
        return RedirectResponse("/gestores/novo?erro=" + quote(erro_foto), status_code=303)

    g = Gestor(
        nome=nome,
        cargo_id=_select_cargo(db, cargo_id, novo_cargo),
        foto=conteudo_foto,
        foto_tipo=tipo_foto,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return RedirectResponse(f"/gestores/{g.id}/editar?ok=" + quote("Gestor cadastrado."), status_code=303)


@router.get("/{gestor_id}/foto", response_class=Response)
def foto(
    gestor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(PAG),
):
    """Foto do gestor (exige login, como as fotos de funcionários)."""
    g = db.get(Gestor, gestor_id)
    if not g or not g.foto:
        raise HTTPException(404, "Foto não encontrada.")
    return Response(content=g.foto, media_type=g.foto_tipo or "image/jpeg")


@router.get("/{gestor_id}/editar", response_class=HTMLResponse, dependencies=[Depends(PAG)])
def editar(
    gestor_id: int,
    request: Request,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    g = db.get(Gestor, gestor_id)
    if not g:
        raise HTTPException(404, "Gestor não encontrado.")
    return render(
        request,
        "gestores/form.html",
        {
            "user": user,
            "gestor": g,
            "cargos": db.query(Cargo).order_by(Cargo.nome).all(),
        },
    )


@router.post("/{gestor_id}/editar", dependencies=[Depends(PAG)])
def atualizar(
    gestor_id: int,
    request: Request,
    nome: str = Form(...),
    cargo_id: int | None = Form(None),
    novo_cargo: str = Form(""),
    foto: UploadFile | None = File(None),
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    g = db.get(Gestor, gestor_id)
    if not g:
        raise HTTPException(404, "Gestor não encontrado.")

    nome = _limpar(nome)
    if not nome:
        return RedirectResponse(f"/gestores/{gestor_id}/editar?erro=" + quote("Informe o nome."), status_code=303)

    conteudo_foto, tipo_foto, erro_foto = ler_foto(foto)
    if erro_foto:
        return RedirectResponse(f"/gestores/{gestor_id}/editar?erro=" + quote(erro_foto), status_code=303)

    g.nome = nome
    g.cargo_id = _select_cargo(db, cargo_id, novo_cargo)
    if conteudo_foto is not None:
        g.foto = conteudo_foto
        g.foto_tipo = tipo_foto
    db.commit()
    return RedirectResponse("/gestores?ok=" + quote("Dados atualizados."), status_code=303)


@router.post("/{gestor_id}/excluir", dependencies=[Depends(PAG)])
def excluir(
    gestor_id: int,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    g = db.get(Gestor, gestor_id)
    if not g:
        raise HTTPException(404, "Gestor não encontrado.")
    db.delete(g)
    db.commit()
    return RedirectResponse("/gestores?ok=" + quote("Gestor excluído."), status_code=303)
