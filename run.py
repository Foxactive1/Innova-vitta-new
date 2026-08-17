#!/usr/bin/env python3
"""
Script de inicialização seguro para Clínica Vida+
Resolve problemas de banco de dados no Termux/Android
"""

import os
import sys

# Força o diretório do script como base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# Garante que a pasta instance existe
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)

# Remove qualquer DATABASE_URL do ambiente que possa interferir
if 'DATABASE_URL' in os.environ:
    del os.environ['DATABASE_URL']

print("=" * 50)
print("InNova Vitta+ — Inicialização")
print("=" * 50)
print(f"Diretório base: {BASE_DIR}")
print(f"Diretório instance: {INSTANCE_DIR}")
print(f"Banco de dados: SQLite")
print("=" * 50)

# Agora importa e executa a aplicação
from app import app, db
from core.models import Paciente, Medico, Atendimento, Consulta, Exame, Pagamento, Receita

with app.app_context():
    print("\nCriando tabelas no banco de dados...")
    db.create_all()
    print("✓ Tabelas criadas com sucesso!")

    # Verifica se já tem dados
    total_pacientes = Paciente.query.count()
    print(f"✓ Pacientes cadastrados: {total_pacientes}")

print("\nIniciando servidor...")
print("Acesse: http://localhost:5000")
print("=" * 50)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)