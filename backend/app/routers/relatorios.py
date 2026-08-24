import csv
import io
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import require_pagina
from ..models import Funcionario, Matricula, Pagina, Setor, Treinamento, User
from ..services import query_situacao
from ..templating import render

router = APIRouter(prefix="/relatorios", tags=["relatorios"])

PAG = require_pagina(Pagina.RELATORIOS)

CATEGORIA_CSV = {"NR": "NR", "CORPORATIVO": "Corporativo"}


def _todas_matriculas(db: Session, hoje: date):
    ms = db.query(Matricula).options(
        joinedload(Matricula.funcionario),
        joinedload(Matricula.treinamento),
    ).join(Funcionario).filter(Funcionario.ativo == True).all()
    return query_situacao(ms, hoje)


@router.get("", response_class=HTMLResponse)
def relatorios(
    request: Request,
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
    funcionario_id: int | None = None,
    treinamento_id: int | None = None,
):
    hoje = date.today()
    matriculas = _todas_matriculas(db, hoje)

    vencidos = [m for m in matriculas if m._situacao == "Vencido"]
    a_vencer = [m for m in matriculas if m._situacao == "A vencer"]
    vencidos.sort(key=lambda m: m.data_validade or date.min)
    a_vencer.sort(key=lambda m: m.data_validade or date.max)

    funcionario = db.get(Funcionario, funcionario_id) if funcionario_id else None
    treinamento = db.get(Treinamento, treinamento_id) if treinamento_id else None

    matriculas_func = None
    matriculas_treino = None
    if funcionario:
        matriculas_func = [m for m in funcionario.matriculas]
        matriculas_func = query_situacao(matriculas_func, hoje)
    if treinamento:
        matriculas_treino = [m for m in treinamento.matriculas if m.funcionario and m.funcionario.ativo]
        matriculas_treino = query_situacao(matriculas_treino, hoje)

    return render(
        request,
        "relatorios/index.html",
        {
            "user": user,
            "hoje": hoje,
            "funcionarios": db.query(Funcionario).filter(Funcionario.ativo == True).order_by(Funcionario.nome).all(),
            "treinamentos": db.query(Treinamento).filter(Treinamento.ativo == True).order_by(Treinamento.nome).all(),
            "setores": db.query(Setor).order_by(Setor.nome).all(),
            "funcionario": funcionario,
            "treinamento": treinamento,
            "matriculas_func": matriculas_func,
            "matriculas_treino": matriculas_treino,
            "vencidos": vencidos,
            "a_vencer": a_vencer,
        },
    )


@router.get("/por-funcionario/{funcionario_id}", response_class=HTMLResponse)
def por_funcionario(
    funcionario_id: int,
    request: Request,
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
):
    f = db.get(Funcionario, funcionario_id)
    if not f:
        raise HTTPException(404, "Funcionário não encontrado.")
    matriculas = query_situacao(f.matriculas, date.today())
    return render(
        request,
        "relatorios/por_funcionario.html",
        {"user": user, "funcionario": f, "matriculas": matriculas, "hoje": date.today()},
    )


@router.get("/por-treinamento/{treinamento_id}", response_class=HTMLResponse)
def por_treinamento(
    treinamento_id: int,
    request: Request,
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
):
    t = db.get(Treinamento, treinamento_id)
    if not t:
        raise HTTPException(404, "Treinamento não encontrado.")
    matriculas = query_situacao(t.matriculas, date.today())
    return render(
        request,
        "relatorios/por_treinamento.html",
        {"user": user, "treinamento": t, "matriculas": matriculas, "hoje": date.today()},
    )


# ------------------------------------------------------------------ exportações CSV

def _csv_seguro(valor) -> str:
    """Neutraliza injeção de fórmulas no Excel (=, +, -, @ no início do texto)."""
    s = "" if valor is None else str(valor)
    if s[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def _csv_response(rows: list[list], filename: str) -> Response:
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM para o Excel reconhecer UTF-8
    writer = csv.writer(buf, delimiter=";")
    writer.writerows([[_csv_seguro(c) for c in row] for row in rows])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/vencidos.csv")
def export_vencidos(
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
):
    hoje = date.today()
    vencidos = [m for m in _todas_matriculas(db, hoje) if m._situacao == "Vencido"]
    vencidos.sort(key=lambda m: m.data_validade or date.min)
    rows = [["Funcionário", "Matrícula", "Setor", "Treinamento", "Norma", "Realização", "Vencimento", "Dias vencido"]]
    for m in vencidos:
        dias = (hoje - (m.data_validade or hoje)).days
        rows.append([
            m.funcionario.nome,
            m.funcionario.matricula or "",
            m.funcionario.setor.nome if m.funcionario.setor else "",
            m.treinamento.nome,
            m.treinamento.norma or "",
            m.data_realizacao.isoformat() if m.data_realizacao else "",
            (m.data_validade or "").isoformat() if m.data_validade else "",
            dias,
        ])
    return _csv_response(rows, "treinamentos_vencidos.csv")


@router.get("/export/a-vencer.csv")
def export_a_vencer(
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
):
    hoje = date.today()
    a_vencer = [m for m in _todas_matriculas(db, hoje) if m._situacao == "A vencer"]
    a_vencer.sort(key=lambda m: m.data_validade or date.max)
    rows = [["Funcionário", "Matrícula", "Setor", "Treinamento", "Norma", "Realização", "Vencimento", "Dias restantes"]]
    for m in a_vencer:
        dias = (m.data_validade - hoje).days if m.data_validade else ""
        rows.append([
            m.funcionario.nome,
            m.funcionario.matricula or "",
            m.funcionario.setor.nome if m.funcionario.setor else "",
            m.treinamento.nome,
            m.treinamento.norma or "",
            m.data_realizacao.isoformat() if m.data_realizacao else "",
            (m.data_validade or "").isoformat() if m.data_validade else "",
            dias,
        ])
    return _csv_response(rows, "treinamentos_a_vencer.csv")


@router.get("/export/funcionario/{funcionario_id}.csv")
def export_funcionario(
    funcionario_id: int,
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
):
    f = db.get(Funcionario, funcionario_id)
    if not f:
        raise HTTPException(404, "Funcionário não encontrado.")
    matriculas = query_situacao(f.matriculas, date.today())
    matriculas.sort(key=lambda m: m.data_validade or date.max)
    rows = [[
        "Funcionário", "Treinamento", "Norma", "Categoria", "Realização", "Vencimento", "Situação"
    ]]
    for m in matriculas:
        rows.append([
            f.nome,
            m.treinamento.nome,
            m.treinamento.norma or "",
            CATEGORIA_CSV.get(m.treinamento.categoria, m.treinamento.categoria),
            m.data_realizacao.isoformat() if m.data_realizacao else "",
            (m.data_validade or "").isoformat() if m.data_validade else "Sem validade",
            m._situacao,
        ])
    nome_arq = f"treinamentos_{f.nome.replace(' ', '_')}.csv"
    return _csv_response(rows, nome_arq)


@router.get("/export/todos.csv")
def export_todos(
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
):
    hoje = date.today()
    matriculas = _todas_matriculas(db, hoje)
    matriculas.sort(key=lambda m: (m.funcionario.nome, m.data_validade or date.max))
    rows = [[
        "Funcionário", "Matrícula", "Setor", "Treinamento", "Norma", "Categoria",
        "Realização", "Vencimento", "Situação",
    ]]
    for m in matriculas:
        rows.append([
            m.funcionario.nome,
            m.funcionario.matricula or "",
            m.funcionario.setor.nome if m.funcionario.setor else "",
            m.treinamento.nome,
            m.treinamento.norma or "",
            CATEGORIA_CSV.get(m.treinamento.categoria, m.treinamento.categoria),
            m.data_realizacao.isoformat() if m.data_realizacao else "",
            (m.data_validade or "").isoformat() if m.data_validade else "",
            m._situacao,
        ])
    return _csv_response(rows, "todos_treinamentos.csv")
