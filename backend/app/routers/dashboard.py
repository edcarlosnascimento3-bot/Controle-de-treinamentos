from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import require_login
from ..models import CategoriaTreinamento, Funcionario, Matricula, Pagina, Role, Treinamento, User
from ..services import dias_para_vencer, query_situacao, situacao_matricula
from ..templating import render
from .auth import router as auth_router

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
    funcionario_id: int | None = Query(None),
):
    hoje = date.today()

    if not user.pode_acessar(Pagina.PAINEL):
        destino = user.primeira_pagina_url
        if destino:
            return RedirectResponse(destino, status_code=307)
        raise HTTPException(
            403,
            "Nenhuma página foi liberada para o seu usuário. Fale com o administrador.",
        )

    if user.role == Role.VISUALIZADOR:
        # Visualizador só acessa a página "Registros de treinamentos".
        return RedirectResponse("/matriculas", status_code=307)

    if user.role == Role.COLABORADOR:
        return _dashboard_colaborador(request, user, db, hoje)

    if user.role == Role.GESTOR:
        return _dashboard_gestor(request, user, db, hoje, funcionario_id)

    total_funcionarios = db.query(func.count(Funcionario.id)).filter(Funcionario.ativo == True).scalar() or 0
    total_treinamentos = db.query(func.count(Treinamento.id)).filter(Treinamento.ativo == True).scalar() or 0
    total_matriculas = (
        db.query(func.count(Matricula.id))
        .join(Funcionario)
        .filter(Funcionario.ativo == True)
        .scalar()
        or 0
    )
    nr_ativos = (
        db.query(func.count(Treinamento.id))
        .filter(Treinamento.categoria == CategoriaTreinamento.NR, Treinamento.ativo == True)
        .scalar()
        or 0
    )

    matriculas = db.query(Matricula).options(
        joinedload(Matricula.funcionario),
        joinedload(Matricula.treinamento),
    ).join(Funcionario).filter(Funcionario.ativo == True).all()
    query_situacao(matriculas, hoje)

    vencidos = [m for m in matriculas if m._situacao in ("Vencido", "Não realizado")]
    a_vencer = [m for m in matriculas if m._situacao == "A vencer"]
    validos = [m for m in matriculas if m._situacao == "Válido"]

    a_vencer.sort(key=lambda m: m.data_validade or date.max)
    vencidos.sort(key=lambda m: (m._situacao == "Não realizado", m.data_validade or date.min), reverse=True)

    sel_funcionario = db.get(Funcionario, funcionario_id) if funcionario_id else None
    sel_matriculas = None
    if sel_funcionario:
        sel_matriculas = query_situacao(sel_funcionario.matriculas, hoje)

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "user": user,
            "hoje": hoje,
            "total_funcionarios": total_funcionarios,
            "total_treinamentos": total_treinamentos,
            "total_matriculas": total_matriculas,
            "nr_ativos": nr_ativos,
            "vencidos": vencidos[:15],
            "qtd_vencidos": len(vencidos),
            "a_vencer": a_vencer[:15],
            "qtd_a_vencer": len(a_vencer),
            "qtd_validos": len(validos),
            "funcionarios": db.query(Funcionario).filter(Funcionario.ativo == True).order_by(Funcionario.nome).all(),
            "sel_funcionario": sel_funcionario,
            "sel_matriculas": sel_matriculas,
            "funcao": "admin_rh",
        },
    )


def _dashboard_gestor(request, user, db, hoje, funcionario_id=None):
    funcionarios = db.query(Funcionario).filter(Funcionario.ativo == True).order_by(Funcionario.nome).all()
    matriculas = db.query(Matricula).options(
        joinedload(Matricula.funcionario),
        joinedload(Matricula.treinamento),
    ).join(Funcionario).filter(Funcionario.ativo == True).all()
    query_situacao(matriculas, hoje)
    vencidos = [m for m in matriculas if m._situacao in ("Vencido", "Não realizado")]
    a_vencer = [m for m in matriculas if m._situacao == "A vencer"]
    vencidos.sort(key=lambda m: (m._situacao == "Não realizado", m.data_validade or date.min), reverse=True)
    a_vencer.sort(key=lambda m: m.data_validade or date.max)
    sel_funcionario = db.get(Funcionario, funcionario_id) if funcionario_id else None
    sel_matriculas = None
    if sel_funcionario:
        sel_matriculas = query_situacao(sel_funcionario.matriculas, hoje)
    return render(
        request,
        "dashboard/dashboard.html",
        {
            "user": user,
            "hoje": hoje,
            "total_funcionarios": len(funcionarios),
            "vencidos": vencidos[:15],
            "qtd_vencidos": len(vencidos),
            "a_vencer": a_vencer[:15],
            "qtd_a_vencer": len(a_vencer),
            "funcionarios": funcionarios,
            "sel_funcionario": sel_funcionario,
            "sel_matriculas": sel_matriculas,
            "funcao": "gestor",
        },
    )


def _dashboard_colaborador(request, user, db, hoje):
    funcionario = user.funcionario
    if not funcionario:
        return render(
            request,
            "dashboard/dashboard.html",
            {
                "user": user,
                "hoje": hoje,
                "funcao": "colaborador",
                "sem_vinculo": True,
            },
        )
    matriculas = funcionario.matriculas
    query_situacao(matriculas, hoje)
    vencidos = [m for m in matriculas if m._situacao in ("Vencido", "Não realizado")]
    a_vencer = [m for m in matriculas if m._situacao == "A vencer"]
    vencidos.sort(key=lambda m: (m._situacao == "Não realizado", m.data_validade or date.min), reverse=True)
    a_vencer.sort(key=lambda m: m.data_validade or date.max)
    return render(
        request,
        "dashboard/dashboard.html",
        {
            "user": user,
            "hoje": hoje,
            "funcionario": funcionario,
            "matriculas": matriculas,
            "vencidos": vencidos,
            "qtd_vencidos": len(vencidos),
            "a_vencer": a_vencer,
            "qtd_a_vencer": len(a_vencer),
            "funcao": "colaborador",
        },
    )
