"""
InNova Vitta+ — Ponto de entrada WSGI
Usado pelo Gunicorn em produção: gunicorn wsgi:app
"""

import os
from app import app, db

# db.create_all() apenas para desenvolvimento local com SQLite.
# Com PostgreSQL/Neon o schema já existe e é gerenciado manualmente.
# No Vercel o filesystem é read-only — nunca executar aqui.
if not os.environ.get("DATABASE_URL") and not os.environ.get("VERCEL"):
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    app.run()
