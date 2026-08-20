import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# ============================================================
# CARREGAR VARIÁVEIS DO NEON
# ============================================================

ENV_FILE = BASE_DIR / ".env1"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

# ============================================================
# CONFIGURAÇÃO
# ============================================================

class Config:

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "chave-secreta-clinica-vida-plus-2025-innova"
    )

    # --- TRATAMENTO DA URL (corrigido) ---
    raw_url = os.environ.get("DATABASE_URL")
    if raw_url:
        # Remove espaços, quebras de linha e aspas extras
        DATABASE_URL = raw_url.strip().strip('"').strip("'")
    else:
        DATABASE_URL = None

    # ========================================================
    # BANCO DE DADOS
    # ========================================================

    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Fallback somente para desenvolvimento local
        SQLALCHEMY_DATABASE_URI = (
            f"sqlite:///{BASE_DIR / 'instance' / 'clinica_vida_plus.db'}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ========================================================
    # DEBUG
    # ========================================================

    DEBUG = os.environ.get(
        "DEBUG",
        "False"
    ).lower() in ("true", "1", "t")

    # ========================================================
    # SQLALCHEMY ENGINE
    # ========================================================

    if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):

        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {
                "check_same_thread": False,
                "timeout": 30,
            },
            "pool_pre_ping": True,
        }

    else:

        # PostgreSQL / Neon
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }