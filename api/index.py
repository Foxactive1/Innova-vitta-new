"""
InNova Vitta+ — Entry point serverless para Vercel
Importa a app Flask e expõe como handler WSGI
"""

import sys
import os

# Adiciona a raiz do projeto ao path para que imports funcionem
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app, db

# Garante criação das tabelas no primeiro cold start
with app.app_context():
    db.create_all()

# O Vercel procura por uma variável chamada 'app' neste módulo
# O @vercel/python detecta automaticamente aplicações WSGI/ASGI
