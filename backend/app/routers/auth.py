from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import TOKEN_COOKIE, get_current_user
from ..models import User
from ..security import create_access_token, verify_password
from ..templating import render

router = APIRouter(prefix="/auth", tags=["auth"])

# Proteção contra força bruta: contagem de falhas por usuário.
# Guardado em memória (reiniciar o servidor zera o contador).
_falhas_login: dict[str, dict] = {}


def _registro_bloqueio(username: str) -> tuple[bool, int]:
    """Retorna (bloqueado_agora, minutos_restantes) para o usuário."""
    reg = _falhas_login.get(username.lower())
    if not reg or not reg.get("ate"):
        return False, 0
    restante = (reg["ate"] - datetime.now()).total_seconds()
    if restante <= 0:
        return False, 0
    return True, int(restante // 60) + 1


def _registrar_falha(username: str) -> int:
    """Soma uma falha e devolve quantas faltam para o bloqueio."""
    reg = _falhas_login.setdefault(username.lower(), {"qtd": 0, "ate": None})
    reg["qtd"] += 1
    return settings.MAX_TENTATIVAS_LOGIN - reg["qtd"]


def _aplicar_bloqueio(username: str) -> None:
    _falhas_login[username.lower()] = {
        "qtd": 0,
        "ate": datetime.now() + timedelta(minutes=settings.BLOQUEIO_LOGIN_MINUTOS),
    }


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: User | None = Depends(get_current_user)):
    if user:
        return RedirectResponse("/", status_code=303)
    return render(request, "auth/login.html")


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip()
    bloqueado, minutos = _registro_bloqueio(username)
    if bloqueado:
        return render(
            request,
            "auth/login.html",
            {"bloqueado": True, "minutos": minutos},
        )

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        restantes = _registrar_falha(username)
        if restantes <= 0:
            _aplicar_bloqueio(username)
            return render(
                request,
                "auth/login.html",
                {"bloqueado": True, "minutos": settings.BLOQUEIO_LOGIN_MINUTOS},
            )
        return render(
            request,
            "auth/login.html",
            {
                "erro": "Usuário ou senha inválidos.",
                "aviso_tentativas": f"Tentativa {settings.MAX_TENTATIVAS_LOGIN - restantes} de {settings.MAX_TENTATIVAS_LOGIN}.",
            },
        )
    if not user.ativo:
        return render(request, "auth/login.html", {"erro": "Usuário inativo. Fale com o administrador."})

    _falhas_login.pop(username.lower(), None)

    token = create_access_token(user.id, user.role)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(
        key=TOKEN_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_HOURS * 60 * 60,
    )
    return resp


@router.post("/logout")
def logout():
    resp = RedirectResponse("/auth/login", status_code=303)
    resp.delete_cookie(TOKEN_COOKIE)
    return resp
