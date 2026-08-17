import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chave-secreta-clinica-vida-plus-2025-innova')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'clinica_vida_plus.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'check_same_thread': False,
            'timeout': 30,
        },
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')