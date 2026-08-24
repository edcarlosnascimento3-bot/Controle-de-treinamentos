from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .database import get_db
from .models import Pagina, Role, User
from .security import decode_token

TOKEN_COOKIE = "access_token"


def extract_token(request: Request) -> str | None:
    # Prefere o cookie (uso via navegador); aceita header Authorization (uso via API).
    token = request.cookies.get(TOKEN_COOKIE)
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth[7:]
    return token


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    token = extract_token(request)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    try:
        user_id = int(payload.get("sub", 0))
    except (TypeError, ValueError):
        return None
    user = db.get(User, user_id)
    if user is None or not user.ativo:
        return None
    return user


def require_login(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Faça login para continuar."
        )
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(require_login)) -> User:
        if user.role not in [r.value for r in roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar esta página.",
            )
        return user

    return checker


def require_pagina(*paginas: Pagina):
    """Exige que o usuário tenha ao menos uma das páginas liberadas pelo administrador.

    Administradores sempre têm acesso.
    """

    def checker(user: User = Depends(require_login)) -> User:
        if user.eh_admin or any(p.value in user.lista_permissoes for p in paginas):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar esta página.",
        )

    return checker


def login_redirect(url: str = "/auth/login") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": url},
    )
