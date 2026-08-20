#!/usr/bin/env python3
"""
InNova Vitta+ — Importação de Medicamentos ANVISA → PostgreSQL/Neon

Características:
- Usa exclusivamente DATABASE_URL do .env1
- Não utiliza SQLite
- Não executa db.create_all()
- Importa em lotes
- Faz rollback apenas da transação com erro
- Evita duplicação pelo NUMERO_REGISTRO_PRODUTO
- Fallback por nome + fabricante quando não existe número de registro
- Trata UTF-8, UTF-8-SIG, Latin-1 e CP1252
- Detecta automaticamente o separador
- Compatível com Flask-SQLAlchemy + psycopg2 + Neon
"""

import os
import sys
import csv
import requests
import urllib3

from dotenv import load_dotenv

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Carrega especificamente o ambiente do Neon
load_dotenv(os.path.join(BASE_DIR, ".env1"))

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL não encontrada no .env1")
    sys.exit(1)

if not DATABASE_URL.startswith(("postgresql://", "postgres://")):
    print("❌ DATABASE_URL não aponta para PostgreSQL.")
    print("   Este script foi criado exclusivamente para Neon/PostgreSQL.")
    sys.exit(1)

# Garante que o diretório do projeto esteja no PATH
sys.path.insert(0, BASE_DIR)

from core.models import db, Medicamento
from app import app

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# ============================================================
# CONFIGURAÇÕES DA ANVISA
# ============================================================

URL_ANVISA_CSV = (
    "https://dados.anvisa.gov.br/dados/"
    "DADOS_ABERTOS_MEDICAMENTOS.csv"
)

ARQUIVO_LOCAL = os.path.join(
    BASE_DIR,
    "dados_anvisa_oficial.csv"
)

TAMANHO_LOTE = 500


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def mostrar_destino():
    """Mostra informações do banco sem exibir a senha."""

    try:
        engine_url = db.engine.url

        print("\n==============================================")
        print(" DESTINO DA IMPORTAÇÃO")
        print("==============================================")
        print(f"Banco : {engine_url.database}")
        print(f"Host  : {engine_url.host}")
        print(f"Driver: {engine_url.drivername}")
        print("Tipo  : PostgreSQL / Neon")
        print("==============================================")

    except Exception as e:
        print(f"❌ Não foi possível identificar o banco: {e}")
        sys.exit(1)


def baixar_base_anvisa():
    """Baixa a base oficial da ANVISA com cache local."""

    if os.path.exists(ARQUIVO_LOCAL):
        tamanho = os.path.getsize(ARQUIVO_LOCAL)

        if tamanho > 0:
            print(
                f"\n📁 Arquivo local encontrado: "
                f"{ARQUIVO_LOCAL}"
            )
            print(
                f"   Tamanho: "
                f"{tamanho / 1024 / 1024:.2f} MB"
            )
            return True

    print("\n⬇️ Baixando base oficial da ANVISA...")
    print("   Isso pode demorar alguns minutos.\n")

    try:
        response = requests.get(
            URL_ANVISA_CSV,
            stream=True,
            timeout=120,
            verify=False
        )

        response.raise_for_status()

        with open(ARQUIVO_LOCAL, "wb") as arquivo:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk:
                    arquivo.write(chunk)

        print("✅ Download concluído.")

        return True

    except Exception as e:

        print(f"❌ Erro no download da ANVISA: {e}")

        return False


def detectar_formato():
    """Detecta encoding e separador do CSV."""

    encodings = [
        "utf-8-sig",
        "utf-8",
        "latin-1",
        "cp1252",
    ]

    separadores = [
        ";",
        ",",
    ]

    for encoding in encodings:

        for separador in separadores:

            try:

                with open(
                    ARQUIVO_LOCAL,
                    "r",
                    encoding=encoding,
                    newline=""
                ) as arquivo:

                    leitor = csv.DictReader(
                        arquivo,
                        delimiter=separador
                    )

                    campos = leitor.fieldnames

                    if campos and "NOME_PRODUTO" in campos:

                        print(
                            f"✅ Encoding detectado: "
                            f"{encoding}"
                        )

                        print(
                            f"✅ Separador detectado: "
                            f"'{separador}'"
                        )

                        return encoding, separador

            except Exception:
                continue

    return None, None


def normalizar(valor):
    """Normaliza valores vindos do CSV."""

    if valor is None:
        return None

    valor = str(valor).strip()

    return valor if valor else None


# ============================================================
# IMPORTAÇÃO
# ============================================================

def popular_do_csv():

    if not baixar_base_anvisa():
        return

    encoding, separador = detectar_formato()

    if not encoding:

        print(
            "\n❌ Não foi possível identificar "
            "o formato do CSV."
        )

        return

    with app.app_context():

        # ----------------------------------------------------
        # Confirma banco
        # ----------------------------------------------------

        mostrar_destino()

        # ----------------------------------------------------
        # Teste de conexão
        # ----------------------------------------------------

        try:

            with db.engine.connect() as conn:
                conn.exec_driver_sql(
                    "SELECT 1"
                )

            print("✅ Conexão com PostgreSQL/Neon OK.")

        except Exception as e:

            print(
                "\n❌ Falha na conexão com o Neon:"
            )

            print(e)

            return

        # ----------------------------------------------------
        # Estado atual
        # ----------------------------------------------------

        try:

            total_existente = (
                Medicamento.query.count()
            )

            print(
                f"\n💊 Medicamentos atualmente "
                f"no Neon: {total_existente}"
            )

        except Exception as e:

            print(
                f"❌ Erro consultando medicamento: {e}"
            )

            return

        # ----------------------------------------------------
        # Confirmação
        # ----------------------------------------------------

        print(
            "\n⚠️ A operação irá inserir/atualizar "
            "dados diretamente no PostgreSQL/Neon."
        )

        resposta = input(
            "\nContinuar? (s/N): "
        )

        if resposta.lower() != "s":

            print("Operação cancelada.")

            return

        # ----------------------------------------------------
        # Mapeamento ANVISA → Modelo
        # ----------------------------------------------------

        mapeamento = {

            "TIPO_PRODUTO":
                "tipo_produto",

            "NOME_PRODUTO":
                "nome",

            "PRINCIPIO_ATIVO":
                "principio_ativo",

            "CATEGORIA_REGULATORIA":
                "categoria_regulatoria",

            "NUMERO_REGISTRO_PRODUTO":
                "numero_registro_produto",

            "NUMERO_PROCESSO":
                "numero_processo",

            "CLASSE_TERAPEUTICA":
                "classe_terapeutica",

            "EMPRESA_DETENTORA_REGISTRO":
                "fabricante",

            "SITUACAO_REGISTRO":
                "situacao_registro",

            "DATA_FINALIZACAO_PROCESSO":
                "data_finalizacao_processo",

            "DATA_VENCIMENTO_REGISTRO":
                "data_vencimento_registro",
        }

        # ----------------------------------------------------
        # Contadores
        # ----------------------------------------------------

        processados = 0
        inseridos = 0
        atualizados = 0
        ignorados = 0
        erros = 0

        # ----------------------------------------------------
        # Leitura
        # ----------------------------------------------------

        try:

            arquivo = open(
                ARQUIVO_LOCAL,
                "r",
                encoding=encoding,
                newline=""
            )

        except Exception as e:

            print(
                f"❌ Erro abrindo CSV: {e}"
            )

            return

        with arquivo:

            leitor = csv.DictReader(
                arquivo,
                delimiter=separador
            )

            for linha in leitor:

                nome = normalizar(
                    linha.get("NOME_PRODUTO")
                )

                # --------------------------------------------
                # Validação
                # --------------------------------------------

                if not nome or nome.startswith("-"):

                    ignorados += 1

                    continue

                processados += 1

                try:

                    # ----------------------------------------
                    # Monta dados
                    # ----------------------------------------

                    dados = {}

                    for coluna_csv, atributo in mapeamento.items():

                        valor = normalizar(
                            linha.get(coluna_csv)
                        )

                        dados[atributo] = valor

                    # ----------------------------------------
                    # Campos complementares
                    # ----------------------------------------

                    situacao = normalizar(
                        linha.get(
                            "SITUACAO_REGISTRO"
                        )
                    )

                    dados["descricao"] = (
                        f"ANVISA – {situacao}"
                        if situacao
                        else "ANVISA"
                    )

                    # O CSV oficial pode não fornecer
                    # esses campos.
                    dados["forma_farmaceutica"] = None
                    dados["dosagem"] = None

                    # ----------------------------------------
                    # Registro ANVISA
                    # ----------------------------------------

                    numero_registro = normalizar(
                        linha.get(
                            "NUMERO_REGISTRO_PRODUTO"
                        )
                    )

                    existente = None

                    if numero_registro:

                        existente = (
                            Medicamento.query
                            .filter_by(
                                numero_registro_produto=
                                numero_registro
                            )
                            .first()
                        )

                    # ----------------------------------------
                    # Fallback nome + fabricante
                    # ----------------------------------------

                    if not existente:

                        fabricante = dados.get(
                            "fabricante"
                        )

                        if not numero_registro:

                            existente = (
                                Medicamento.query
                                .filter_by(
                                    nome=nome,
                                    fabricante=fabricante
                                )
                                .first()
                            )

                    # ----------------------------------------
                    # UPDATE
                    # ----------------------------------------

                    if existente:

                        for atributo, valor in dados.items():

                            setattr(
                                existente,
                                atributo,
                                valor
                            )

                        atualizados += 1

                    # ----------------------------------------
                    # INSERT
                    # ----------------------------------------

                    else:

                        novo = Medicamento(
                            **dados
                        )

                        db.session.add(novo)

                        inseridos += 1

                    # ----------------------------------------
                    # Commit por lote
                    # ----------------------------------------

                    if processados % TAMANHO_LOTE == 0:

                        db.session.commit()

                        print(
                            f"   📦 {processados:,} "
                            f"processados | "
                            f"➕ {inseridos:,} inseridos | "
                            f"🔄 {atualizados:,} atualizados | "
                            f"❌ {erros:,} erros"
                        )

                except Exception as e:

                    erros += 1

                    db.session.rollback()

                    print(
                        f"   ⚠️ Erro em "
                        f"'{nome}': {e}"
                    )

                    continue

        # ----------------------------------------------------
        # Commit final
        # ----------------------------------------------------

        try:

            db.session.commit()

        except Exception as e:

            db.session.rollback()

            print(
                f"\n❌ Erro no commit final: {e}"
            )

            return

        # ----------------------------------------------------
        # Resultado
        # ----------------------------------------------------

        try:

            total_final = (
                Medicamento.query.count()
            )

        except Exception:

            total_final = "indisponível"

        print("\n")
        print("==============================================")
        print(" IMPORTAÇÃO FINALIZADA")
        print("==============================================")
        print(
            f"Processados : {processados:,}"
        )
        print(
            f"Inseridos   : {inseridos:,}"
        )
        print(
            f"Atualizados : {atualizados:,}"
        )
        print(
            f"Ignorados   : {ignorados:,}"
        )
        print(
            f"Erros       : {erros:,}"
        )
        print(
            f"Total Neon  : {total_final}"
        )
        print("==============================================")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("==============================================")
    print(" INNOVA VITTA+")
    print(" ANVISA → POSTGRESQL / NEON")
    print("==============================================")

    popular_do_csv()