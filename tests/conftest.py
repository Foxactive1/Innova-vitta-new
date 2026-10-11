"""
Configuração compartilhada dos testes pytest.
"""

import os
import sys
import tempfile

import pytest

# Garante que a raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def app():
    """Cria uma instância da aplicação em modo de teste."""
    # Configura variáveis de ambiente antes de importar config
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DEBUG"] = "False"

    from app import create_app
    from core.models import db as _db

    app = create_app("config.Config")
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,  # Desativa CSRF nos testes
    })

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture()
def client(app):
    """Retorna um cliente de teste Flask."""
    return app.test_client()


@pytest.fixture()
def db(app):
    """Retorna a instância do SQLAlchemy dentro do contexto da app."""
    from core.models import db as _db
    return _db
