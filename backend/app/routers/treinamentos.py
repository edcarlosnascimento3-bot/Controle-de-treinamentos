from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_pagina, require_roles
from ..models import Categoria, CategoriaTreinamento, Pagina, Role, Treinamento, User
from ..templating import render

router = APIRouter(prefix="/treinamentos", tags=["treinamentos"])

PERM = require_roles(Role.ADMIN, Role.RH)
PAG = require_pagina(Pagina.TREINAMENTOS)


def _limpar(value: str | None) -> str | None:
    v = (value or "").strip()
    return v or None


def _categorias(db: Session):
    return db.query(Categoria).order_by(Categoria.nome).all()


def _resolver_categoria(db: Session, value: str) -> Categoria | None:
    v = (value or "").strip()
    if not v:
        return None
    return db.query(Categoria).filter(func.lower(Categoria.nome) == v.lower()).first()


def _parse_carga_horaria(value: str) -> float | None:
    """Converte a carga horária; retorna None quando vazia.

    Levanta ValueError para entradas inválidas ou negativas.
    """
    v = (value or "").strip().replace(",", ".")
    if not v:
        return None
    numero = float(v)
    if numero <= 0 or numero > 1000:
        raise ValueError("carga")
    return numero


def _parse_validade_meses(value: str) -> int | None:
    """Converte a validade em meses; None = não expira."""
    v = (value or "").strip()
    if not v:
        return None
    numero = int(v)
    if numero < 0 or numero > 1200:
        raise ValueError("validade")
    return numero or None


@router.get("", response_class=HTMLResponse)
def listar(
    request: Request,
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
    busca: str = "",
    categoria: str = "",
):
    q = db.query(Treinamento)
    if busca:
        termo = f"%{busca.strip()}%"
        q = q.filter(or_(Treinamento.nome.ilike(termo), Treinamento.norma.ilike(termo)))
    if categoria:
        q = q.filter(Treinamento.categoria == categoria)

    treinamentos = q.order_by(Treinamento.nome).all()
    return render(
        request,
        "treinamentos/list.html",
        {
            "user": user,
            "treinamentos": treinamentos,
            "categorias": _categorias(db),
            "busca": busca,
            "categoria": categoria,
            "pode_editar": user.role in (Role.ADMIN, Role.RH),
        },
    )


@router.get("/novo", response_class=HTMLResponse, dependencies=[Depends(PAG)])
def novo(request: Request, user: User = Depends(PERM), db: Session = Depends(get_db)):
    return render(
        request,
        "treinamentos/form.html",
        {"user": user, "treinamento": None, "categorias": _categorias(db)},
    )


@router.post("", dependencies=[Depends(PAG)])
def criar(
    request: Request,
    nome: str = Form(...),
    categoria: str = Form(CategoriaTreinamento.CORPORATIVO.value),
    norma: str = Form(""),
    descricao: str = Form(""),
    carga_horaria: str = Form(""),
    validade_meses: str = Form(""),
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    nome = _limpar(nome)
    if not nome:
        return RedirectResponse("/treinamentos/novo?erro=Informe+o+nome.", status_code=303)

    cat = _resolver_categoria(db, categoria)
    if not cat:
        return RedirectResponse("/treinamentos/novo?erro=" + quote("Selecione uma categoria válida."), status_code=303)

    try:
        carga = _parse_carga_horaria(carga_horaria)
        validade = _parse_validade_meses(validade_meses)
    except ValueError:
        return RedirectResponse("/treinamentos/novo?erro=" + quote("Carga horária e validade devem ser números válidos (ex.: 8 e 12)."), status_code=303)

    t = Treinamento(
        nome=nome,
        categoria=cat.nome,
        norma=_limpar(norma),
        descricao=_limpar(descricao),
        carga_horaria=carga,
        validade_meses=validade,
    )
    db.add(t)
    db.commit()
    return RedirectResponse(f"/treinamentos/{t.id}?ok=" + quote("Treinamento cadastrado."), status_code=303)


@router.get("/{treinamento_id}", response_class=HTMLResponse)
def detalhe(
    treinamento_id: int,
    request: Request,
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
):
    t = db.get(Treinamento, treinamento_id)
    if not t:
        raise HTTPException(404, "Treinamento não encontrado.")
    registros = [m for m in t.matriculas if m.funcionario and m.funcionario.ativo]
    return render(
        request,
        "treinamentos/detail.html",
        {
            "user": user,
            "treinamento": t,
            "registros": registros,
            "qtd_registros": len(registros),
            "pode_editar": user.role in (Role.ADMIN, Role.RH),
        },
    )


@router.get("/{treinamento_id}/editar", response_class=HTMLResponse, dependencies=[Depends(PAG)])
def editar(
    treinamento_id: int,
    request: Request,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    t = db.get(Treinamento, treinamento_id)
    if not t:
        raise HTTPException(404, "Treinamento não encontrado.")
    return render(
        request,
        "treinamentos/form.html",
        {"user": user, "treinamento": t, "categorias": _categorias(db)},
    )


@router.post("/{treinamento_id}/editar", dependencies=[Depends(PAG)])
def atualizar(
    treinamento_id: int,
    request: Request,
    nome: str = Form(...),
    categoria: str = Form(CategoriaTreinamento.CORPORATIVO.value),
    norma: str = Form(""),
    descricao: str = Form(""),
    carga_horaria: str = Form(""),
    validade_meses: str = Form(""),
    ativo: str = Form("on"),
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    t = db.get(Treinamento, treinamento_id)
    if not t:
        raise HTTPException(404, "Treinamento não encontrado.")

    nome = _limpar(nome)
    if not nome:
        return RedirectResponse(f"/treinamentos/{treinamento_id}/editar?erro=Informe+o+nome.", status_code=303)

    cat = _resolver_categoria(db, categoria)
    if not cat:
        return RedirectResponse(f"/treinamentos/{treinamento_id}/editar?erro=" + quote("Selecione uma categoria válida."), status_code=303)

    try:
        carga = _parse_carga_horaria(carga_horaria)
        validade = _parse_validade_meses(validade_meses)
    except ValueError:
        return RedirectResponse(f"/treinamentos/{treinamento_id}/editar?erro=" + quote("Carga horária e validade devem ser números válidos (ex.: 8 e 12)."), status_code=303)

    t.nome = nome
    t.categoria = cat.nome
    t.norma = _limpar(norma)
    t.descricao = _limpar(descricao)
    t.carga_horaria = carga
    t.validade_meses = validade
    t.ativo = ativo == "on"
    db.commit()
    return RedirectResponse(f"/treinamentos/{treinamento_id}?ok=" + quote("Dados atualizados."), status_code=303)


@router.post("/{treinamento_id}/excluir", dependencies=[Depends(PAG)])
def excluir(
    treinamento_id: int,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    t = db.get(Treinamento, treinamento_id)
    if not t:
        raise HTTPException(404, "Treinamento não encontrado.")
    if t.matriculas:
        return RedirectResponse("/treinamentos?erro=" + quote("Treinamento possui registros. Desative em vez de excluir."), status_code=303)
    db.delete(t)
    db.commit()
    return RedirectResponse("/treinamentos?ok=" + quote("Treinamento excluído."), status_code=303)
