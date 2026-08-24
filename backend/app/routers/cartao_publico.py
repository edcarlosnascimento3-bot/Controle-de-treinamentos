import hmac
import io
import unicodedata
from datetime import date

import segno
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Funcionario
from ..services import query_situacao
from ..templating import render
from ._helpers import (
    cookie_confirmacao,
    url_base,
    url_cartao_publico,
    validar_token_cartao,
)

router = APIRouter(prefix="/c", tags=["cartao-publico"])

COOKIE_MAX_AGE = 8 * 60 * 60


def _carregar(db: Session, funcionario_id: int, token: str) -> Funcionario:
    """Valida a autorização (token assinado) antes de expor qualquer dado."""
    if not validar_token_cartao(funcionario_id, token):
        raise HTTPException(404, "Link inválido ou expirado.")
    f = db.get(Funcionario, funcionario_id)
    if not f:
        raise HTTPException(404, "Funcionário não encontrado.")
    return f


def _normalizar_nome(value: str) -> str:
    """Remove acentos, espaços extras e ignora maiúsculas/minúsculas."""
    sem_acento = unicodedata.normalize("NFKD", value or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def _autorizado(request: Request, funcionario_id: int, token: str) -> bool:
    nome_cookie, valor = cookie_confirmacao(funcionario_id, token)
    recebido = request.cookies.get(nome_cookie, "")
    import hmac as _hmac

    return _hmac.compare_digest(recebido, valor)


@router.get("/{funcionario_id}/{token}", response_class=HTMLResponse)
def cartao(
    funcionario_id: int,
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Cartão de treinamentos acessível apenas por link autorizado + checagem do nome cadastrado."""
    f = _carregar(db, funcionario_id, token)
    if not _autorizado(request, f.id, token):
        return render(
            request,
            "funcionarios/cartao_confirmar.html",
            {
                "user": None,
                "action": f"{url_cartao_publico(f.id)}/confirmar",
                "erro": None,
            },
        )
    matriculas = query_situacao(f.matriculas)
    return render(
        request,
        "funcionarios/cartao.html",
        {
            "user": None,
            "funcionario": f,
            "matriculas": matriculas,
            "url_cartao": f"{url_base(request)}{url_cartao_publico(f.id)}",
            "url_qr": f"{url_cartao_publico(f.id)}/qr.svg",
            "url_foto": f"{url_cartao_publico(f.id)}/foto",
            "hoje": date.today().strftime("%d/%m/%Y"),
        },
    )


@router.post("/{funcionario_id}/{token}/confirmar", response_class=HTMLResponse)
def confirmar(
    funcionario_id: int,
    token: str,
    request: Request,
    nome: str = Form(...),
    db: Session = Depends(get_db),
):
    """Checagem do nome cadastrado; ao acertar, emite cookie de autorização."""
    f = _carregar(db, funcionario_id, token)
    action = f"{url_cartao_publico(f.id)}/confirmar"
    if not _normalizar_nome(nome):
        raise HTTPException(422, "Informe o nome cadastrado.")
    if _normalizar_nome(nome) != _normalizar_nome(f.nome or ""):
        return render(
            request,
            "funcionarios/cartao_confirmar.html",
            {
                "user": None,
                "action": action,
                "erro": "Nome não confere com o cadastro. Tente novamente.",
            },
        )
    nome_cookie, valor = cookie_confirmacao(f.id, token)
    resposta = RedirectResponse(url_cartao_publico(f.id), status_code=303)
    resposta.set_cookie(
        nome_cookie,
        valor,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return resposta


@router.get("/{funcionario_id}/{token}/qr.svg", response_class=Response)
def qr_code(
    funcionario_id: int,
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """QR Code apontando para o link assinado do cartão."""
    f = _carregar(db, funcionario_id, token)
    destino = f"{url_base(request)}{url_cartao_publico(f.id)}"
    qr = segno.make(destino, error="m", boost_error=True)
    buf = io.BytesIO()
    qr.save(buf, kind="svg", scale=8, border=1, dark="#1e3a8a", light="#ffffff")
    return Response(content=buf.getvalue(), media_type="image/svg+xml")


@router.get("/{funcionario_id}/{token}/foto", response_class=Response)
def foto(
    funcionario_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    """Foto exibida no cartão público (mesma proteção por token)."""
    f = _carregar(db, funcionario_id, token)
    if not f.foto:
        raise HTTPException(404, "Foto não encontrada.")
    return Response(content=f.foto, media_type=f.foto_tipo or "image/jpeg")
