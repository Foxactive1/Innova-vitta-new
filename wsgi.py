"""
InNova Vitta+ — Ponto de entrada WSGI
Usado pelo Gunicorn em produção: gunicorn wsgi:app
"""

from app import app, db

# Garante que as tabelas existam no primeiro boot em produção
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run()
