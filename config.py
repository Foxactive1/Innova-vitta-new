import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Apenas desenvolvimento local. Segredos de produção devem ser configurados
# diretamente no provedor (Vercel, Render, Railway etc.).
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"true", "1", "t", "yes", "on"}


class Config:
    DEBUG = _env_bool("DEBUG", False)

    # Em produção não há segredo default. Isso evita iniciar com uma chave
    # conhecida/versionada. Em dev, forneça SECRET_KEY no .env.
    SECRET_KEY = os.environ.get("SECRET_KEY")

    raw_url = os.environ.get("DATABASE_URL")
    DATABASE_URL = raw_url.strip().strip('"').strip("'") if raw_url else None

    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'clinica_vida_plus.db'}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"check_same_thread": False, "timeout": 30},
            "pool_pre_ping": True,
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }

    # Bootstrap de autenticação sem alteração de schema.
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_ROLE = os.environ.get("ADMIN_ROLE", "admin")
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

    # Segurança de sessão.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", not DEBUG)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    WTF_CSRF_ENABLED = True
    WTF_CSRF_SSL_STRICT = _env_bool("WTF_CSRF_SSL_STRICT", not DEBUG)
