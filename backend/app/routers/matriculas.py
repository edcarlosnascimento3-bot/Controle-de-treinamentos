from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import require_login, require_pagina, require_roles
from ..models import Categoria, CategoriaTreinamento, Certificado, Funcionario, Matricula, Pagina, Role, Treinamento, User
from ..services import (
    CertificadoInvalido,
    calcular_data_validade,
    caminho_certificado,
    query_situacao,
    salvar_certificado,
)
from ..templating import render

router = APIRouter(prefix="/matriculas", tags=["matriculas"])

PERM = require_roles(Role.ADMIN, Role.RH)
PAG = require_pagina(Pagina.MATRICULAS)


def _parse_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def _limpar(value: str | None) -> str | None:
    v = (value or "").strip()
    return v or None


def _detalhe_cadastro(db: Session):
    return {
        "funcionarios": db.query(Funcionario).filter(Funcionario.ativo == True).order_by(Funcionario.nome).all(),
        "treinamentos": db.query(Treinamento).filter(Treinamento.ativo == True).order_by(Treinamento.nome).all(),
    }


@router.get("", response_class=HTMLResponse)
def listar(
    request: Request,
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
    busca: str = "",
    situacao: str = "",
    categoria: str = "",
):
    hoje = date.today()
    q = db.query(Matricula).options(
        joinedload(Matricula.funcionario),
        joinedload(Matricula.treinamento),
    ).join(Funcionario).filter(Funcionario.ativo == True)

    if busca:
        termo = f"%{busca.strip()}%"
        q = q.filter(
            or_(
                Funcionario.nome.ilike(termo),
                Funcionario.matricula.ilike(termo),
            )
        )
    if categoria:
        q = q.join(Treinamento).filter(Treinamento.categoria == categoria)

    matriculas = q.order_by(Matricula.data_realizacao.desc()).all()
    matriculas = query_situacao(matriculas, hoje)

    if situacao and situacao != "todas":
        matriculas = [m for m in matriculas if m._situacao == situacao]

    return render(
        request,
        "matriculas/list.html",
        {
            "user": user,
            "matriculas": matriculas,
            "categorias": db.query(Categoria).order_by(Categoria.nome).all(),
            "busca": busca,
            "situacao": situacao,
            "categoria": categoria,
            "hoje": hoje,
            "pode_editar": user.role in (Role.ADMIN, Role.RH),
        },
    )


@router.get("/nova", response_class=HTMLResponse, dependencies=[Depends(PAG)])
def nova(
    request: Request,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
    funcionario_id: int | None = None,
    treinamento_id: int | None = None,
):
    ctx = _detalhe_cadastro(db)
    ctx.update({"user": user, "matricula": None, "funcionario_id": funcionario_id, "treinamento_id": treinamento_id})
    return render(request, "matriculas/form.html", ctx)


@router.post("", dependencies=[Depends(PAG)])
def criar(
    request: Request,
    funcionario_id: int = Form(...),
    treinamento_id: int = Form(...),
    data_realizacao: str = Form(""),
    instrutor: str = Form(""),
    aprovado: str = Form("on"),
    observacoes: str = Form(""),
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    f = db.get(Funcionario, funcionario_id)
    t = db.get(Treinamento, treinamento_id)
    if not f or not t:
        raise HTTPException(404, "Funcionário ou treinamento não encontrado.")

    data = _parse_date(data_realizacao)
    if not data:
        return RedirectResponse("/matriculas/nova?erro=Informe+a+data+de+realização.", status_code=303)

    m = Matricula(
        funcionario_id=f.id,
        treinamento_id=t.id,
        data_realizacao=data,
        data_validade=calcular_data_validade(data, t.validade_meses),
        instrutor=_limpar(instrutor),
        aprovado=aprovado == "on",
        observacoes=_limpar(observacoes),
    )
    db.add(m)
    db.commit()
    return RedirectResponse(f"/matriculas/{m.id}?ok=" + quote("Treinamento registrado."), status_code=303)


@router.get("/{matricula_id}", response_class=HTMLResponse)
def detalhe(
    matricula_id: int,
    request: Request,
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
):
    m = db.get(Matricula, matricula_id)
    if not m:
        raise HTTPException(404, "Registro não encontrado.")

    from ..services import dias_para_vencer

    situacao = query_situacao([m])[0]._situacao
    return render(
        request,
        "matriculas/detail.html",
        {
            "user": user,
            "matricula": m,
            "situacao": situacao,
            "dias": dias_para_vencer(m.data_validade),
            "pode_editar": user.role in (Role.ADMIN, Role.RH),
        },
    )


@router.get("/{matricula_id}/editar", response_class=HTMLResponse, dependencies=[Depends(PAG)])
def editar(
    matricula_id: int,
    request: Request,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    m = db.get(Matricula, matricula_id)
    if not m:
        raise HTTPException(404, "Registro não encontrado.")
    ctx = _detalhe_cadastro(db)
    ctx.update({"user": user, "matricula": m, "funcionario_id": m.funcionario_id, "treinamento_id": m.treinamento_id})
    return render(request, "matriculas/form.html", ctx)


@router.post("/{matricula_id}/editar", dependencies=[Depends(PAG)])
def atualizar(
    matricula_id: int,
    request: Request,
    funcionario_id: int = Form(...),
    treinamento_id: int = Form(...),
    data_realizacao: str = Form(""),
    instrutor: str = Form(""),
    aprovado: str = Form("on"),
    observacoes: str = Form(""),
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    m = db.get(Matricula, matricula_id)
    if not m:
        raise HTTPException(404, "Registro não encontrado.")
    t = db.get(Treinamento, treinamento_id)
    data = _parse_date(data_realizacao)
    if data is None and data_realizacao.strip():
        return RedirectResponse(f"/matriculas/{matricula_id}/editar?erro=Dados+inválidos.", status_code=303)
    if not t:
        return RedirectResponse(f"/matriculas/{matricula_id}/editar?erro=Dados+inválidos.", status_code=303)

    m.funcionario_id = funcionario_id
    m.treinamento_id = t.id
    m.data_realizacao = data
    m.data_validade = calcular_data_validade(data, t.validade_meses) if data else None
    m.instrutor = _limpar(instrutor)
    m.aprovado = aprovado == "on"
    m.observacoes = _limpar(observacoes)
    db.commit()
    return RedirectResponse(f"/matriculas/{matricula_id}?ok=" + quote("Registro atualizado."), status_code=303)


@router.post("/{matricula_id}/excluir", dependencies=[Depends(PAG)])
def excluir(
    matricula_id: int,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    m = db.get(Matricula, matricula_id)
    if not m:
        raise HTTPException(404, "Registro não encontrado.")
    if m.certificado and m.certificado.arquivo_nome:
        caminho = caminho_certificado(m.certificado.arquivo_nome)
        if caminho.exists():
            caminho.unlink(missing_ok=True)
    db.delete(m)
    db.commit()
    return RedirectResponse("/matriculas?ok=" + quote("Registro excluído."), status_code=303)


# ------------------------------------------------------------------ certificados

@router.post("/{matricula_id}/certificado", dependencies=[Depends(PAG)])
def enviar_certificado(
    matricula_id: int,
    request: Request,
    arquivo: UploadFile | None = None,
    numero: str = Form(""),
    data_emissao: str = Form(""),
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    m = db.get(Matricula, matricula_id)
    if not m:
        raise HTTPException(404, "Registro não encontrado.")

    cert = m.certificado
    if not cert:
        cert = Certificado(matricula_id=m.id)
        db.add(cert)

    cert.numero = _limpar(numero)
    if data_emissao:
        cert.data_emissao = _parse_date(data_emissao) or date.today()
    elif not cert.data_emissao:
        cert.data_emissao = date.today()

    # Sem novo arquivo enviado: preserva o PDF já armazenado.
    if not arquivo or not arquivo.filename:
        db.commit()
        return RedirectResponse(f"/matriculas/{matricula_id}?ok=" + quote("Certificado salvo."), status_code=303)

    try:
        salvo = salvar_certificado(arquivo)
    except CertificadoInvalido as e:
        db.rollback()
        return RedirectResponse(f"/matriculas/{matricula_id}?erro={quote(str(e))}", status_code=303)

    if salvo:
        antigo = cert.arquivo_nome
        cert.arquivo_nome = salvo[1]
        if antigo and antigo != cert.arquivo_nome:
            caminho = caminho_certificado(antigo)
            if caminho.exists():
                caminho.unlink(missing_ok=True)

    db.commit()
    return RedirectResponse(f"/matriculas/{matricula_id}?ok=" + quote("Certificado salvo."), status_code=303)


@router.get("/{matricula_id}/certificado/download")
def baixar_certificado(
    matricula_id: int,
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
):
    m = db.get(Matricula, matricula_id)
    if not m or not m.certificado or not m.certificado.arquivo_nome:
        raise HTTPException(404, "Certificado não encontrado.")

    caminho = caminho_certificado(m.certificado.arquivo_nome)
    if not caminho.exists():
        raise HTTPException(404, "Arquivo não encontrado no servidor.")
    nome = f"certificado_{m.funcionario.nome.replace(' ', '_')}_{m.treinamento.nome.replace(' ', '_')}{caminho.suffix}"
    return FileResponse(caminho, filename=nome)


@router.post("/{matricula_id}/certificado/remover", dependencies=[Depends(PAG)])
def remover_certificado(
    matricula_id: int,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    m = db.get(Matricula, matricula_id)
    if not m or not m.certificado:
        raise HTTPException(404, "Certificado não encontrado.")
    if m.certificado.arquivo_nome:
        caminho = caminho_certificado(m.certificado.arquivo_nome)
        if caminho.exists():
            caminho.unlink(missing_ok=True)
    db.delete(m.certificado)
    db.commit()
    return RedirectResponse(f"/matriculas/{matricula_id}?ok=" + quote("Certificado removido."), status_code=303)
