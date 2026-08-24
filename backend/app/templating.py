from pathlib import Path

from fastapi.templating import Jinja2Templates

from .config import settings
from .models import MENU_LATERAL, PAGINA_LABELS, PAGINA_SOMENTE_ADMIN

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _paginas_sistema() -> list[dict]:
    """Todas as páginas do menu, na ordem do lateral, para os formulários de usuário."""
    return [
        {
            "chave": item["pagina"].value,
            "rotulo": PAGINA_LABELS[item["pagina"]],
            "url": item["url"],
            "somente_admin": item["pagina"] in PAGINA_SOMENTE_ADMIN,
        }
        for item in MENU_LATERAL
    ]


PAGINAS_SISTEMA = _paginas_sistema()


def render(request, template_name: str, context: dict | None = None, user=None, status_code: int = 200):
    ctx = {
        "request": request,
        "user": user,
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "ok": request.query_params.get("ok"),
        "erro": request.query_params.get("erro"),
        "paginas_sistema": PAGINAS_SISTEMA,
        "menu_itens": [],
    }
    if context:
        ctx.update(context)
    usuario = ctx.get("user") or user
    if usuario is not None:
        try:
            ctx["menu_itens"] = usuario.menu_itens
        except Exception:
            ctx["menu_itens"] = []
    return templates.TemplateResponse(request, template_name, ctx, status_code=status_code)
