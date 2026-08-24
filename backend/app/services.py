import calendar
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from .config import settings
from .models import CategoriaTreinamento, Matricula, Treinamento


def add_months(d: date, months: int) -> date:
    """Soma meses a uma data tratando corretamente fim de mês (31/01 + 1m = 28/02)."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calcular_data_validade(data_realizacao: date, validade_meses: int | None) -> date | None:
    """Data de validade = data de realização + validade em meses. None = não expira."""
    if not validade_meses:
        return None
    return add_months(data_realizacao, validade_meses)


def situacao(vencimento: date | None, hoje: date | None = None) -> str:
    """Situação de uma matrícula: Válido | A vencer | Vencido | Sem validade."""
    if vencimento is None:
        return "Sem validade"
    hoje = hoje or date.today()
    if vencimento < hoje:
        return "Vencido"
    if vencimento <= hoje + timedelta(days=settings.ALERTA_DIAS):
        return "A vencer"
    return "Válido"


def situacao_matricula(matricula: Matricula, hoje: date | None = None) -> str:
    if matricula.data_realizacao is None:
        return "Não realizado"
    return situacao(matricula.data_validade, hoje)


def dias_para_vencer(vencimento: date | None, hoje: date | None = None) -> int | None:
    if vencimento is None:
        return None
    hoje = hoje or date.today()
    return (vencimento - hoje).days


MAX_CERTIFICADO_BYTES = 10 * 1024 * 1024

# Tipos aceitos: PDF, PNG e JPG (por content-type ou extensão do arquivo).
TIPOS_CERTIFICADO = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}
EXTENSOES_CERTIFICADO = {".pdf", ".png", ".jpg", ".jpeg"}


class CertificadoInvalido(ValueError):
    """Arquivo de certificado recusado por formato ou tamanho."""


def salvar_certificado(uploaded_file) -> tuple[str, str] | None:
    """Salva o arquivo de certificado e retorna (nome_original, nome_salvo).

    Levanta CertificadoInvalido quando o formato ou o tamanho não são aceitos.
    """
    if not uploaded_file or not uploaded_file.filename:
        return None

    content_type = (uploaded_file.content_type or "").lower()
    sufixo = Path(uploaded_file.filename).suffix.lower()

    if not TIPOS_CERTIFICADO.get(content_type) and sufixo not in EXTENSOES_CERTIFICADO:
        raise CertificadoInvalido("Formato não permitido. Envie um arquivo PDF, PNG ou JPG.")

    conteudo = uploaded_file.file.read()
    if len(conteudo) > MAX_CERTIFICADO_BYTES:
        raise CertificadoInvalido("Arquivo muito grande (máximo 10 MB).")

    nome_salvo = f"{uuid4().hex}{sufixo or '.pdf'}"
    destino = settings.upload_dir_path / nome_salvo
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo)
    return uploaded_file.filename, nome_salvo


def caminho_certificado(nome_salvo: str) -> Path:
    return settings.upload_dir_path / nome_salvo


def query_situacao(query, hoje: date | None = None):
    """Anexa a situação calculada a cada matrícula da lista (para exibição)."""
    hoje = hoje or date.today()
    for m in query:
        m._situacao = situacao_matricula(m, hoje)
        m._dias = dias_para_vencer(m.data_validade, hoje)
    return query
