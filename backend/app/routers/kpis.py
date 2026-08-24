from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import require_pagina
from ..models import Funcionario, Matricula, Pagina, Treinamento, User
from ..templating import render

router = APIRouter(prefix="/kpis", tags=["kpis"])

PAG = require_pagina(Pagina.KPIS)

MESES = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]

CATEGORIA_LABEL = {"NR": "NR", "CORPORATIVO": "Corporativo"}


def _todas_matriculas(db: Session) -> list[Matricula]:
    return (
        db.query(Matricula)
        .options(
            joinedload(Matricula.funcionario),
            joinedload(Matricula.treinamento),
        )
        .join(Funcionario)
        .filter(Funcionario.ativo == True)
        .all()
    )


def _unidades(db: Session) -> list[str]:
    return [
        u[0]
        for u in db.query(Funcionario.unidade)
        .distinct()
        .filter(Funcionario.unidade.isnot(None))
        .order_by(Funcionario.unidade)
        .all()
    ]


def _anos(matriculas: list[Matricula]) -> list[int]:
    anos = sorted({m.data_realizacao.year for m in matriculas if m.data_realizacao})
    return anos or [date.today().year]


@router.get("", response_class=HTMLResponse)
def kpis(
    request: Request,
    user: User = Depends(PAG),
    db: Session = Depends(get_db),
    ano: int | None = None,
):
    matriculas = _todas_matriculas(db)
    anos = _anos(matriculas)
    if ano is not None:
        try:
            ano = int(ano)
        except (ValueError, TypeError):
            ano = None
    if ano is None or ano not in anos:
        ano = max(anos)

    unidades = _unidades(db)
    unidades_data = []
    for unidade in unidades:
        ms = [m for m in matriculas if m.funcionario and m.funcionario.unidade == unidade]
        ms_ano = [m for m in ms if m.data_realizacao and m.data_realizacao.year == ano]

        treinamentos_mes = [0] * 12
        treinamentos_detalhe_mes: list[list[dict]] = [[] for _ in range(12)]
        pessoas_mes = [set() for _ in range(12)]
        horas_mes = [0.0] * 12
        for m in ms_ano:
            i = m.data_realizacao.month - 1
            treinamentos_mes[i] += 1
            treinamentos_detalhe_mes[i].append({
                "nome": m.treinamento.nome,
                "categoria": CATEGORIA_LABEL.get(m.treinamento.categoria, m.treinamento.categoria or "—"),
                "carga": m.treinamento.carga_horaria or 0,
                "funcionario": m.funcionario.nome if m.funcionario else "—",
            })
            pessoas_mes[i].add(m.funcionario_id)
            horas_mes[i] += m.treinamento.carga_horaria or 0

        turno = Counter(m.funcionario.turno or "Sem turno" for m in ms)
        turno_items = sorted(turno.items(), key=lambda x: (-x[1], x[0]))

        unidades_data.append({
            "unidade": unidade,
            "treinamentos_mes": treinamentos_mes,
            "treinamentos_detalhe_mes": treinamentos_detalhe_mes,
            "pessoas_mes": [len(s) for s in pessoas_mes],
            "horas_mes": [round(h, 1) for h in horas_mes],
            "turno_labels": [k for k, _ in turno_items],
            "turno_values": [v for _, v in turno_items],
        })

    tipo = Counter(
        CATEGORIA_LABEL.get(m.treinamento.categoria, m.treinamento.categoria or "—")
        for m in matriculas
        if m.treinamento and m.data_realizacao and m.data_realizacao.year == ano
    )
    tipo_items = sorted(tipo.items(), key=lambda x: (-x[1], x[0]))

    return render(
        request,
        "kpis/index.html",
        {
            "user": user,
            "ano": ano,
            "anos": anos,
            "meses": MESES,
            "unidades_data": unidades_data,
            "tipo_labels": [k for k, _ in tipo_items],
            "tipo_values": [v for _, v in tipo_items],
        },
    )
