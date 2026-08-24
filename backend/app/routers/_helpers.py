import hashlib
import hmac

from fastapi import Request, UploadFile

from ..config import settings

MAX_FOTO_BYTES = 10 * 1024 * 1024


def ler_foto(foto: UploadFile | None) -> tuple[bytes | None, str | None, str | None]:
    """Lê a foto enviada, limitando tamanho e tipos permitidos.

    Retorna (conteudo, tipo, erro). `erro` preenchido indica que a imagem
    foi recusada; nesse caso o conteúdo é None.
    """
    if not foto or not foto.filename:
        return None, None, None
    if not foto.content_type or not foto.content_type.startswith("image/"):
        return None, None, "O arquivo deve ser uma imagem (JPG, PNG, GIF, WEBP)."
    conteudo = foto.file.read()
    if len(conteudo) > MAX_FOTO_BYTES:
        return None, None, "Imagem muito grande (máximo 10 MB)."
    return conteudo, foto.content_type, None


def url_base(request: Request) -> str:
    """URL pública base preferindo PUBLIC_BASE_URL configurada."""
    base = settings.PUBLIC_BASE_URL.strip().rstrip("/")
    if base:
        return base
    return str(request.base_url).rstrip("/")


def _assinatura_cartao(funcionario_id: int) -> str:
    """Assinatura HMAC determinística e não adivinhável por funcionário."""
    msg = f"cartao:{funcionario_id}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:32]


def url_cartao_publico(funcionario_id: int) -> str:
    token = _assinatura_cartao(funcionario_id)
    return f"/c/{funcionario_id}/{token}"


def validar_token_cartao(funcionario_id: int, token: str) -> bool:
    return hmac.compare_digest(_assinatura_cartao(funcionario_id), token or "")


def _assinatura_confirmacao(funcionario_id: int, token: str) -> str:
    """Assinatura que autoriza o navegador a abrir o cartão após checar o nome."""
    msg = f"cartao-confirm:{funcionario_id}:{token}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:32]


def cookie_confirmacao(funcionario_id: int, token: str) -> tuple[str, str]:
    """Par (nome_do_cookie, valor) usado como autorização pós-checagem de nome."""
    return f"cartao_ok_{funcionario_id}", _assinatura_confirmacao(funcionario_id, token)
