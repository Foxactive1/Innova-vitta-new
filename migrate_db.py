import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DB_PATH = os.path.join(
    BASE_DIR,
    'instance',
    'clinica_vida_plus.db'
)

print("=" * 65)
print("InNova Vitta+ - Migração do banco de dados")
print("=" * 65)

print(f"\nBanco:")
print(DB_PATH)

if not os.path.exists(DB_PATH):
    print("\n❌ Banco de dados não encontrado.")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


def colunas_tabela(tabela):
    cursor.execute(
        f"PRAGMA table_info({tabela})"
    )

    return [
        coluna[1]
        for coluna in cursor.fetchall()
    ]


def adicionar_coluna(tabela, coluna, definicao):

    colunas = colunas_tabela(tabela)

    if coluna in colunas:

        print(
            f"✓ {tabela}.{coluna} já existe."
        )

        return

    print(
        f"+ Adicionando {tabela}.{coluna}..."
    )

    cursor.execute(
        f"""
        ALTER TABLE {tabela}
        ADD COLUMN {coluna} {definicao}
        """
    )

    print(
        f"✓ {tabela}.{coluna} adicionada."
    )


# =========================================================
# CONSULTA
# =========================================================

print("\n[ CONSULTA ]")

adicionar_coluna(
    'consulta',
    'servico_id',
    'INTEGER'
)

adicionar_coluna(
    'consulta',
    'valor',
    'NUMERIC(10, 2) DEFAULT 0'
)


# =========================================================
# EXAME
# =========================================================

print("\n[ EXAME ]")

adicionar_coluna(
    'exame',
    'servico_id',
    'INTEGER'
)

adicionar_coluna(
    'exame',
    'valor',
    'NUMERIC(10, 2) DEFAULT 0'
)


# =========================================================
# COMMIT
# =========================================================

conn.commit()


# =========================================================
# VERIFICAÇÃO
# =========================================================

print("\n" + "=" * 65)
print("VERIFICAÇÃO FINAL")
print("=" * 65)


for tabela in ['consulta', 'exame']:

    print(f"\nTabela: {tabela}")

    colunas = colunas_tabela(tabela)

    for coluna in colunas:
        print(f"  ✓ {coluna}")


conn.close()

print("\n" + "=" * 65)
print("✓ Migração concluída!")
print("=" * 65)