from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import require_pagina, require_roles
from ..models import Cargo, CategoriaTreinamento, Funcionario, Matricula, Pagina, Role, Setor, Treinamento, User
from ..services import query_situacao
from ..templating import render
from ._helpers import ler_foto, url_base, url_cartao_publico

router = APIRouter(prefix="/funcionarios", tags=["funcionarios"])

PERM = require_roles(Role.ADMIN, Role.RH)
PAG_FUNC = require_pagina(Pagina.FUNCIONARIOS)
PAG_INATIVOS = require_pagina(Pagina.INATIVOS)


def _parse_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def _limpar(value: str | None) -> str | None:
    v = (value or "").strip()
    return v or None


TREINAMENTO_INTEGRACAO = "Integração das áreas"


def _treinamento_integracao(db: Session) -> Treinamento:
    """Localiza o treinamento de integração pela flag (sobrevive a renomeações)."""
    t = db.query(Treinamento).filter(Treinamento.integracao.is_(True)).first()
    if t:
        return t
    t = (
        db.query(Treinamento)
        .filter(func.lower(Treinamento.nome) == TREINAMENTO_INTEGRACAO.lower())
        .first()
    )
    if t:
        t.integracao = True
        return t
    t = Treinamento(
        nome=TREINAMENTO_INTEGRACAO,
        categoria=CategoriaTreinamento.CORPORATIVO,
        ativo=True,
        integracao=True,
    )
    db.add(t)
    db.flush()
    return t


def _matricula_integracao(db: Session, funcionario: Funcionario) -> None:
    """Garante a matrícula pendente do treinamento de integração para o colaborador."""
    t = _treinamento_integracao(db)
    ja_existe = any(m.treinamento_id == t.id for m in funcionario.matriculas)
    if not ja_existe:
        db.add(Matricula(funcionario_id=funcionario.id, treinamento_id=t.id, data_realizacao=None))


def _select_setor(db: Session, nome_novo: str | None, setor_id: int | None) -> int | None:
    nome = _limpar(nome_novo)
    if nome:
        s = db.query(Setor).filter(func.lower(Setor.nome) == nome.lower()).first()
        if not s:
            s = Setor(nome=nome)
            db.add(s)
            db.flush()
        return s.id
    return setor_id


def _select_cargo(db: Session, nome_novo: str | None, cargo_id: int | None) -> int | None:
    nome = _limpar(nome_novo)
    if nome:
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
    user: User = Depends(PAG_FUNC),
    db: Session = Depends(get_db),
    nome: str = "",
    setor_id: int | None = None,
):
    nomes = [
        r[0]
        for r in db.query(Funcionario.nome)
        .filter(Funcionario.ativo == True)
        .order_by(Funcionario.nome)
        .all()
    ]
    q = db.query(Funcionario).options(
        joinedload(Funcionario.setor),
        joinedload(Funcionario.cargo),
    ).filter(Funcionario.ativo == True)
    if nome:
        q = q.filter(Funcionario.nome == nome)
    if setor_id:
        q = q.filter(Funcionario.setor_id == setor_id)

    funcionarios = q.order_by(Funcionario.nome).all()
    setores = db.query(Setor).order_by(Setor.nome).all()
    return render(
        request,
        "funcionarios/list.html",
        {
            "user": user,
            "funcionarios": funcionarios,
            "nomes": nomes,
            "nome": nome,
            "setores": setores,
            "setor_id": setor_id,
            "pode_editar": user.role in (Role.ADMIN, Role.RH),
        },
    )


@router.get("/novo", response_class=HTMLResponse, dependencies=[Depends(PAG_FUNC)])
def novo(
    request: Request,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    return render(
        request,
        "funcionarios/form.html",
        {
            "user": user,
            "funcionario": None,
            "setores": db.query(Setor).order_by(Setor.nome).all(),
            "cargos": db.query(Cargo).order_by(Cargo.nome).all(),
            "treinamentos": db.query(Treinamento).filter(Treinamento.ativo == True).order_by(Treinamento.nome).all(),
        },
    )


@router.post("", dependencies=[Depends(PAG_FUNC)])
def criar(
    request: Request,
    nome: str = Form(...),
    cpf: str = Form(""),
    matricula: str = Form(""),
    email: str = Form(""),
    telefone: str = Form(""),
    data_admissao: str = Form(""),
    data_demissao: str = Form(""),
    turno: str = Form(""),
    unidade: str = Form(""),
    setor_id: int | None = Form(None),
    cargo_id: int | None = Form(None),
    novo_setor: str = Form(""),
    novo_cargo: str = Form(""),
    treinamentos_ids: list[int] = Form([]),
    foto: UploadFile | None = File(None),
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    nome = _limpar(nome)
    if not nome:
        return RedirectResponse("/funcionarios/novo?erro=" + quote("Informe o nome."), status_code=303)

    conteudo_foto, tipo_foto, erro_foto = ler_foto(foto)
    if erro_foto:
        return RedirectResponse("/funcionarios/novo?erro=" + quote(erro_foto), status_code=303)
    f = Funcionario(
        nome=nome,
        cpf=_limpar(cpf),
        matricula=_limpar(matricula),
        email=_limpar(email),
        telefone=_limpar(telefone),
        data_admissao=_parse_date(data_admissao),
        data_demissao=_parse_date(data_demissao),
        turno=_limpar(turno),
        unidade=_limpar(unidade),
        setor_id=_select_setor(db, novo_setor, setor_id),
        cargo_id=_select_cargo(db, novo_cargo, cargo_id),
        foto=conteudo_foto,
        foto_tipo=tipo_foto,
    )
    ids_obrigatorios = [i for i in treinamentos_ids if i]
    if ids_obrigatorios:
        f.treinamentos_obrigatorios = (
            db.query(Treinamento).filter(Treinamento.id.in_(ids_obrigatorios)).all()
        )
    try:
        db.add(f)
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse("/funcionarios/novo?erro=" + quote("CPF ou matrícula já cadastrados."), status_code=303)
    try:
        _matricula_integracao(db, f)
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse(f"/funcionarios/{f.id}?ok=" + quote("Funcionário cadastrado."), status_code=303)


@router.get("/inativos", response_class=HTMLResponse)
def inativos(
    request: Request,
    user: User = Depends(PAG_INATIVOS),
    db: Session = Depends(get_db),
    nome: str = "",
):
    nomes = [
        r[0]
        for r in db.query(Funcionario.nome)
        .filter(Funcionario.ativo == False)
        .order_by(Funcionario.nome)
        .all()
    ]
    q = db.query(Funcionario).options(
        joinedload(Funcionario.setor),
        joinedload(Funcionario.cargo),
    ).filter(Funcionario.ativo == False)
    if nome:
        q = q.filter(Funcionario.nome == nome)
    funcionarios = q.order_by(Funcionario.nome).all()
    return render(
        request,
        "funcionarios/inativos.html",
        {
            "user": user,
            "funcionarios": funcionarios,
            "nomes": nomes,
            "nome": nome,
            "pode_editar": user.role in (Role.ADMIN, Role.RH),
        },
    )


@router.get("/{funcionario_id}/foto", response_class=Response)
def foto(
    funcionario_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_pagina(Pagina.FUNCIONARIOS, Pagina.INATIVOS)),
):
    """Foto/avatar do funcionário (exigirá login; o cartão usa link assinado)."""
    f = db.get(Funcionario, funcionario_id)
    if not f or not f.foto:
        raise HTTPException(404, "Foto não encontrada.")
    return Response(content=f.foto, media_type=f.foto_tipo or "image/jpeg")


@router.get("/{funcionario_id}", response_class=HTMLResponse)
def detalhe(
    funcionario_id: int,
    request: Request,
    user: User = Depends(PAG_FUNC),
    db: Session = Depends(get_db),
):
    f = db.get(Funcionario, funcionario_id)
    if not f:
        raise HTTPException(404, "Funcionário não encontrado.")

    matriculas = query_situacao(f.matriculas)
    return render(
        request,
        "funcionarios/detail.html",
        {
            "user": user,
            "funcionario": f,
            "matriculas": matriculas,
            "pode_editar": user.role in (Role.ADMIN, Role.RH),
            "url_cartao": f"{url_base(request)}{url_cartao_publico(funcionario_id)}",
            "url_qr": f"{url_cartao_publico(funcionario_id)}/qr.svg",
        },
    )


@router.get("/{funcionario_id}/editar", response_class=HTMLResponse, dependencies=[Depends(PAG_FUNC)])
def editar(
    funcionario_id: int,
    request: Request,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    f = db.get(Funcionario, funcionario_id)
    if not f:
        raise HTTPException(404, "Funcionário não encontrado.")
    return render(
        request,
        "funcionarios/form.html",
        {
            "user": user,
            "funcionario": f,
            "setores": db.query(Setor).order_by(Setor.nome).all(),
            "cargos": db.query(Cargo).order_by(Cargo.nome).all(),
            "treinamentos": db.query(Treinamento).filter(Treinamento.ativo == True).order_by(Treinamento.nome).all(),
        },
    )


@router.post("/{funcionario_id}/editar", dependencies=[Depends(PAG_FUNC)])
def atualizar(
    funcionario_id: int,
    request: Request,
    nome: str = Form(...),
    cpf: str = Form(""),
    matricula: str = Form(""),
    email: str = Form(""),
    telefone: str = Form(""),
    data_admissao: str = Form(""),
    data_demissao: str = Form(""),
    turno: str = Form(""),
    unidade: str = Form(""),
    setor_id: int | None = Form(None),
    cargo_id: int | None = Form(None),
    novo_setor: str = Form(""),
    novo_cargo: str = Form(""),
    treinamentos_ids: list[int] = Form([]),
    foto: UploadFile | None = File(None),
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    f = db.get(Funcionario, funcionario_id)
    if not f:
        raise HTTPException(404, "Funcionário não encontrado.")

    nome = _limpar(nome)
    if not nome:
        return RedirectResponse(f"/funcionarios/{funcionario_id}/editar?erro=Informe+o+nome.", status_code=303)

    conteudo_foto, tipo_foto, erro_foto = ler_foto(foto)
    if erro_foto:
        return RedirectResponse(f"/funcionarios/{funcionario_id}/editar?erro=" + quote(erro_foto), status_code=303)
    if conteudo_foto is not None:
        f.foto = conteudo_foto
        f.foto_tipo = tipo_foto
    f.nome = nome
    f.cpf = _limpar(cpf)
    f.matricula = _limpar(matricula)
    f.email = _limpar(email)
    f.telefone = _limpar(telefone)
    f.data_admissao = _parse_date(data_admissao)
    f.data_demissao = _parse_date(data_demissao)
    f.turno = _limpar(turno)
    f.unidade = _limpar(unidade)
    f.setor_id = _select_setor(db, novo_setor, setor_id)
    f.cargo_id = _select_cargo(db, novo_cargo, cargo_id)
    ids_obrigatorios = [i for i in treinamentos_ids if i]
    f.treinamentos_obrigatorios = (
        db.query(Treinamento).filter(Treinamento.id.in_(ids_obrigatorios)).all()
        if ids_obrigatorios
        else []
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse(f"/funcionarios/{funcionario_id}/editar?erro=" + quote("CPF ou matrícula já cadastrados."), status_code=303)
    return RedirectResponse(f"/funcionarios/{funcionario_id}?ok=" + quote("Dados atualizados."), status_code=303)


@router.post("/{funcionario_id}/inativar", dependencies=[Depends(PAG_FUNC)])
def inativar(
    funcionario_id: int,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    """Move o funcionário para a página Inativos (some das seleções e listagens ativas)."""
    f = db.get(Funcionario, funcionario_id)
    if not f:
        raise HTTPException(404, "Funcionário não encontrado.")
    f.ativo = False
    db.commit()
    return RedirectResponse("/funcionarios/inativos?ok=" + quote(f"{f.nome} foi movido para Inativos."), status_code=303)


@router.post("/{funcionario_id}/reativar", dependencies=[Depends(PAG_FUNC), Depends(PAG_INATIVOS)])
def reativar(
    funcionario_id: int,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    f = db.get(Funcionario, funcionario_id)
    if not f:
        raise HTTPException(404, "Funcionário não encontrado.")
    f.ativo = True
    db.commit()
    try:
        _matricula_integracao(db, f)
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse("/funcionarios/inativos?ok=" + quote(f"{f.nome} foi reativado."), status_code=303)


@router.post("/{funcionario_id}/excluir", dependencies=[Depends(PAG_FUNC)])
def excluir(
    funcionario_id: int,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    f = db.get(Funcionario, funcionario_id)
    if not f:
        raise HTTPException(404, "Funcionário não encontrado.")
    if f.matriculas:
        return RedirectResponse("/funcionarios?erro=" + quote("Funcionário possui treinamentos. Marque como inativo em vez de excluir."), status_code=303)
    db.delete(f)
    db.commit()
    return RedirectResponse("/funcionarios?ok=" + quote("Funcionário excluído."), status_code=303)
