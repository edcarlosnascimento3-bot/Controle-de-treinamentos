import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, text

from .config import BASE_DIR, ROOT_DIR, settings
from .database import Base, SessionLocal, engine
from .models import Categoria, PERMISSOES_PADRAO, Role, User
from .security import hash_password
from .templating import render
from .routers import (
    auth,
    cargos,
    cartao_publico,
    categorias,
    dashboard,
    funcionarios,
    gestores,
    kpis,
    matriculas,
    relatorios,
    setores,
    treinamentos,
    usuarios,
)

# ------------------------------------------------------------------ logs

LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _inicializar_banco()
    yield


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

# Serve arquivos estáticos (CSS/JS do frontend)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(funcionarios.router)
app.include_router(kpis.router)
app.include_router(treinamentos.router)
app.include_router(matriculas.router)
app.include_router(relatorios.router)
app.include_router(usuarios.router)
app.include_router(setores.router)
app.include_router(cargos.router)
app.include_router(gestores.router)
app.include_router(categorias.router)
app.include_router(cartao_publico.router)


def _garantir_coluna_permissoes() -> None:
    """Cria a coluna users.permissoes em bancos já existentes (modo local,
    onde não há alembic) e preenche as permissões padrão de quem ainda
    não tem configuração salva (NULL)."""
    from sqlalchemy import inspect

    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    colunas = [c["name"] for c in insp.get_columns("users")]
    if "permissoes" not in colunas:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN permissoes VARCHAR(500)"))
        logger.info("Coluna users.permissoes criada.")

    db = SessionLocal()
    try:
        alterados = 0
        for u in db.query(User).filter(User.permissoes.is_(None)).all():
            padrao = PERMISSOES_PADRAO.get(Role(u.role), [])
            u.permissoes = ",".join(p.value for p in padrao)
            alterados += 1
        if alterados:
            db.commit()
            logger.info("Permissões padrão aplicadas a %d usuário(s).", alterados)
    finally:
        db.close()


def _inicializar_banco() -> None:
    """Cria diretórios, tabelas e o usuário administrador inicial (modo local)."""
    settings.upload_dir_path.mkdir(parents=True, exist_ok=True)
    ROOT_DIR.joinpath("data").mkdir(parents=True, exist_ok=True)

    # Modo local (SQLite): as tabelas são criadas automaticamente na primeira execução.
    # Em produção (PostgreSQL): rode `alembic upgrade head` antes de iniciar o app.
    if settings.is_sqlite:
        Base.metadata.create_all(bind=engine)
        _garantir_coluna_permissoes()

    db = SessionLocal()
    try:
        if db.query(Categoria).count() == 0:
            db.add_all([Categoria(nome="NR"), Categoria(nome="CORPORATIVO")])
            db.commit()
            logger.info("Categorias padrão criadas (NR, CORPORATIVO).")

        existe_admin = db.query(func.count(User.id)).filter(User.username == settings.ADMIN_USERNAME).scalar() or 0
        if existe_admin == 0:
            admin = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                nome="Administrador",
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
                ativo=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Usuário administrador criado: %s", settings.ADMIN_USERNAME)
        else:
            logger.info("Banco de dados já inicializado.")
    finally:
        db.close()


# ------------------------------------------------------------------ handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code in (401, 307):
        return RedirectResponse(f"/auth/login?erro=Faça+login+para+continuar.", status_code=303)
    if exc.status_code == 404:
        return render(request, "errors/erro.html", {"user": None, "codigo": 404, "mensagem": "Página não encontrada."}, status_code=404)
    if exc.status_code == 403:
        return render(request, "errors/erro.html", {"user": None, "codigo": 403, "mensagem": str(exc.detail)}, status_code=403)
    return render(request, "errors/erro.html", {"user": None, "codigo": exc.status_code, "mensagem": str(exc.detail)}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Erro interno em %s %s", request.method, request.url.path)
    return render(request, "errors/erro.html", {"user": None, "codigo": 500, "mensagem": "Erro interno do servidor."}, status_code=500)
