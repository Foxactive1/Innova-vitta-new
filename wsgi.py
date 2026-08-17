# Arquivo de entrada para servidores WSGI (Gunicorn, uWSGI, etc.)
# Uso: gunicorn wsgi:app

from app import app

if __name__ == "__main__":
    app.run()
