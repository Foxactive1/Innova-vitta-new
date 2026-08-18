"""
InNova Vitta+ — Configuração da aplicação
Suporta SQLite (dev/Termux) e PostgreSQL (Vercel + Supabase/Neon)
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Detecta se está rodando no Vercel
ON_VERCEL = bool(os.environ.get('VERCEL'))


class Config:
    # ── Segurança ──────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError(
            "SECRET_KEY não definida. "
            "Configure a variável de ambiente no painel do Vercel."
        )

    # ── Banco de dados ─────────────────────────────────────────────────────
    # No Vercel, DATABASE_URL é obrigatória (PostgreSQL via Supabase ou Neon)
    # Localmente, cai para SQLite
    _db_url = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'clinica_vida_plus.db')
    )

    # Railway/Supabase/Neon às vezes usam prefixo legado 'postgres://'
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Pool de conexões ───────────────────────────────────────────────────
    _is_sqlite = _db_url.startswith('sqlite')

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        **(
            {'connect_args': {'check_same_thread': False, 'timeout': 30}}
            if _is_sqlite else
            # PostgreSQL no ambiente serverless: pool mínimo para evitar
            # esgotar conexões entre cold starts
            {'pool_size': 1, 'max_overflow': 0}
        ),
    }

    # ── Debug ──────────────────────────────────────────────────────────────
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
