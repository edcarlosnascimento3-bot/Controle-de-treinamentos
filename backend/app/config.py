from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Caminhos absolutos para funcionar independentemente do diretório atual
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
ROOT_DIR = BASE_DIR.parent  # raiz do projeto


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Controle de Treinamentos"
    APP_VERSION: str = "1.0.0"

    # Segurança
    SECRET_KEY: str = "troque-esta-chave-em-producao-pelo-menos-32-caracteres"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 12

    # Envia o cookie de sessão apenas por HTTPS. Ative (true) quando o site
    # estiver publicado com domínio seguro; em rede local mantenha false.
    COOKIE_SECURE: bool = False

    # Proteção contra força bruta no login
    MAX_TENTATIVAS_LOGIN: int = 5
    BLOQUEIO_LOGIN_MINUTOS: int = 5

    # Banco de dados — SQLite local / PostgreSQL online (trocar no .env)
    DATABASE_URL: str = f"sqlite:///{(ROOT_DIR / 'data' / 'app.db').as_posix()}"

    # Uploads de certificados
    UPLOAD_DIR: str = str(ROOT_DIR / "data" / "uploads")

    # URL pública usada no QR Code do cartão do funcionário.
    # Local: informe o IP do PC (ex.: http://192.168.0.10:8000) para escanear pelo celular.
    # Produção: informe o domínio (ex.: https://treinamentos.empresa.com).
    # Vazio = usa a própria URL da requisição.
    PUBLIC_BASE_URL: str = ""

    # Alertas de vencimento (dias antes do vencimento)
    ALERTA_DIAS: int = 60

    # Usuário administrador inicial
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@empresa.local"
    ADMIN_PASSWORD: str = "admin123"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def upload_dir_path(self) -> Path:
        return Path(self.UPLOAD_DIR)


settings = Settings()
