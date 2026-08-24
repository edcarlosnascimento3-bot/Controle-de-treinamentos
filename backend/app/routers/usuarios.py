from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from ..models import MENU_LATERAL, PAGINA_LABELS, PAGINA_SOMENTE_ADMIN, Pagina, Role, User
from ..security import hash_password
from ..templating import render

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

PERM = require_roles(Role.ADMIN)


def _limpar(value: str | None) -> str | None:
    v = (value or "").strip()
    return v or None


def _chaves_validas() -> set[str]:
    return {p.value for p in Pagina}


def _normalizar_permissoes(role: Role, permissoes: list[str]) -> str:
    """Filtra as chaves recebidas do formulário; admin recebe todas."""
    if role == Role.ADMIN:
        chaves = _chaves_validas()
    else:
        validas = _chaves_validas()
        chaves = {p for p in permissoes if p in validas}
    # mantém a ordem do menu lateral
    ordenadas = [p.value for p in Pagina if p in chaves]
    return ",".join(ordenadas)


def _outros_admins_ativos(db: Session, usuario_id: int) -> int:
    """Quantidade de administradores ativos excluindo-se o usuário informado."""
    return (
        db.query(User)
        .filter(User.role == Role.ADMIN, User.ativo == True, User.id != usuario_id)
        .count()
    )


@router.get("", response_class=HTMLResponse)
def listar(
    request: Request,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    usuarios = db.query(User).order_by(User.username).all()
    paginas_form = [p for p in MENU_LATERAL if p["pagina"] not in PAGINA_SOMENTE_ADMIN]
    return render(
        request,
        "usuarios/list.html",
        {
            "user": user,
            "usuarios": usuarios,
            "paginas_form": paginas_form,
            "pagina_labels": PAGINA_LABELS,
        },
    )


@router.post("")
def criar(
    request: Request,
    username: str = Form(...),
    nome: str = Form(...),
    email: str = Form(""),
    senha: str = Form(...),
    role: str = Form(Role.VISUALIZADOR.value),
    permissoes: list[str] = Form([]),
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    username = _limpar(username)
    nome = _limpar(nome)
    if not username or not nome or not senha:
        return RedirectResponse("/usuarios?erro=" + quote("Preencha usuário, nome e senha."), status_code=303)
    if len(senha) < 8:
        return RedirectResponse("/usuarios?erro=" + quote("A senha deve ter ao menos 8 caracteres."), status_code=303)

    if db.query(User).filter(func.lower(User.username) == username.lower()).first():
        return RedirectResponse("/usuarios?erro=" + quote("Nome de usuário já existe."), status_code=303)

    try:
        novo_role = Role(role)
        u = User(
            username=username,
            nome=nome,
            email=_limpar(email),
            password_hash=hash_password(senha),
            role=novo_role,
            permissoes=_normalizar_permissoes(novo_role, permissoes),
            ativo=True,
        )
        db.add(u)
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse("/usuarios?erro=" + quote("Não foi possível criar o usuário (e-mail duplicado?)."), status_code=303)
    return RedirectResponse("/usuarios?ok=" + quote("Usuário criado."), status_code=303)


@router.post("/{usuario_id}/editar")
def atualizar(
    usuario_id: int,
    request: Request,
    nome: str = Form(...),
    email: str = Form(""),
    senha: str = Form(""),
    role: str = Form(Role.VISUALIZADOR.value),
    ativo: str = Form("on"),
    permissoes: list[str] = Form([]),
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    u = db.get(User, usuario_id)
    if not u:
        raise HTTPException(404, "Usuário não encontrado.")

    nome = _limpar(nome)
    if not nome:
        return RedirectResponse("/usuarios?erro=" + quote("Informe o nome."), status_code=303)

    u.nome = nome
    u.email = _limpar(email)

    novo_role = Role(role)
    sera_ativo = ativo == "on"

    if u.id == user.id and u.role != novo_role:
        return RedirectResponse("/usuarios?erro=" + quote("Você não pode alterar o próprio nível de acesso."), status_code=303)

    if u.role == Role.ADMIN and u.ativo and (novo_role != Role.ADMIN or not sera_ativo):
        if _outros_admins_ativos(db, u.id) == 0:
            return RedirectResponse("/usuarios?erro=" + quote("O sistema precisa de pelo menos um administrador ativo."), status_code=303)

    if u.id == user.id and not sera_ativo:
        return RedirectResponse("/usuarios?erro=" + quote("Você não pode desativar o próprio usuário."), status_code=303)

    u.role = novo_role
    u.ativo = sera_ativo
    u.permissoes = _normalizar_permissoes(novo_role, permissoes)
    if senha:
        if len(senha) < 8:
            return RedirectResponse("/usuarios?erro=" + quote("A senha deve ter ao menos 8 caracteres."), status_code=303)
        u.password_hash = hash_password(senha)

    if u.id == user.id and u.ativo is False:
        return RedirectResponse("/usuarios?erro=" + quote("Você não pode desativar o próprio usuário."), status_code=303)

    db.commit()
    return RedirectResponse("/usuarios?ok=" + quote("Usuário atualizado."), status_code=303)


@router.post("/{usuario_id}/excluir")
def excluir(
    usuario_id: int,
    user: User = Depends(PERM),
    db: Session = Depends(get_db),
):
    u = db.get(User, usuario_id)
    if not u:
        raise HTTPException(404, "Usuário não encontrado.")
    if u.id == user.id:
        return RedirectResponse("/usuarios?erro=" + quote("Você não pode excluir o próprio usuário."), status_code=303)
    if u.role == Role.ADMIN and u.ativo and _outros_admins_ativos(db, u.id) == 0:
        return RedirectResponse("/usuarios?erro=" + quote("O sistema precisa de pelo menos um administrador ativo."), status_code=303)
    db.delete(u)
    db.commit()
    return RedirectResponse("/usuarios?ok=" + quote("Usuário excluído."), status_code=303)
