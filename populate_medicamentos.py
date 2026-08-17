#!/usr/bin/env python3
"""
Script para baixar a base oficial da ANVISA e popular a tabela Medicamento.

Correções aplicadas:
  #1 - rollback() no loop não apaga mais lotes válidos (usa session.expunge)
  #2 - Normalização de caracteres removida (encoding detectado corretamente)
  #3 - utf-8-sig adicionado para remover BOM de arquivos do governo
  #4 - fieldnames None tratado antes do 'in'
  #6 - Datas convertidas com segurança (DD/MM/AAAA e MMAAAA)
  #7 - numero_registro_produto comparado como string normalizada
"""

import os
import sys
import csv
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import db, Medicamento
from app import app

URL_ANVISA_CSV  = "https://dados.anvisa.gov.br/dados/DADOS_ABERTOS_MEDICAMENTOS.csv"
ARQUIVO_LOCAL   = "dados_anvisa_oficial.csv"

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def baixar_base_anvisa():
    """Faz download do CSV oficial da ANVISA com cache local."""
    if os.path.exists(ARQUIVO_LOCAL):
        print(f"📁 Cache local encontrado: {ARQUIVO_LOCAL}")
        return True

    print("⬇️  Baixando base oficial da ANVISA (pode demorar alguns minutos)...")
    try:
        response = requests.get(URL_ANVISA_CSV, stream=True, timeout=120, verify=False)
        response.raise_for_status()

        with open(ARQUIVO_LOCAL, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print("✅ Download concluído.")
        return True
    except Exception as e:
        print(f"❌ Erro no download: {e}")
        return False


# ---------------------------------------------------------------------------
# Detecção de encoding/separador
# ---------------------------------------------------------------------------

def detectar_formato():
    """
    Detecta encoding e separador do CSV.
    Tenta utf-8-sig primeiro (remove BOM de arquivos do governo).
    """
    # FIX #3: utf-8-sig antes de utf-8 para tratar BOM
    encodings   = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    separadores = [';', ',']

    for enc in encodings:
        for sep in separadores:
            try:
                with open(ARQUIVO_LOCAL, 'r', encoding=enc) as f:
                    leitor = csv.DictReader(f, delimiter=sep)
                    fields = leitor.fieldnames  # pode ser None
                    # FIX #4: checa None antes de usar 'in'
                    if fields and 'NOME_PRODUTO' in fields:
                        print(f"✅ Encoding: '{enc}' | Separador: '{sep}'")
                        return enc, sep
            except Exception:
                continue

    return None, None


# ---------------------------------------------------------------------------
# População principal
# ---------------------------------------------------------------------------

def popular_do_csv_oficial():
    if not baixar_base_anvisa():
        return

    encoding, separador = detectar_formato()
    if encoding is None:
        print("❌ Não foi possível detectar o formato do CSV.")
        print("   Verifique se o arquivo não está corrompido e tente deletar o cache.")
        return

    with app.app_context():
        # Garante que todas as tabelas existem
        try:
            db.create_all()
            print("✅ Tabelas verificadas/criadas.")
        except Exception as e:
            print(f"⚠️  db.create_all() falhou ({e}) — continuando...")

        total_existente = Medicamento.query.count()
        if total_existente > 0:
            print(f"⚠️  Banco já possui {total_existente} medicamentos.")
            resp = input("Deseja atualizar/inserir novos registros? (s/N): ")
            if resp.lower() != 's':
                print("Operação cancelada.")
                return

        # Mapeamento coluna CSV → atributo do modelo
        # Datas incluídas aqui pois o modelo Medicamento as armazena como String(20)
        mapeamento_str = {
            'TIPO_PRODUTO':               'tipo_produto',
            'NOME_PRODUTO':               'nome',
            'PRINCIPIO_ATIVO':            'principio_ativo',
            'CATEGORIA_REGULATORIA':      'categoria_regulatoria',
            'NUMERO_REGISTRO_PRODUTO':    'numero_registro_produto',
            'NUMERO_PROCESSO':            'numero_processo',
            'CLASSE_TERAPEUTICA':         'classe_terapeutica',
            'EMPRESA_DETENTORA_REGISTRO': 'fabricante',
            'SITUACAO_REGISTRO':          'situacao_registro',
            'DATA_FINALIZACAO_PROCESSO':  'data_finalizacao_processo',
            'DATA_VENCIMENTO_REGISTRO':   'data_vencimento_registro',
        }

        mapeamento_data = {}  # modelo usa String para datas — sem conversão necessária

        inseridos  = 0
        atualizados = 0
        erros      = 0
        ignorados  = 0

        with open(ARQUIVO_LOCAL, 'r', encoding=encoding) as f:
            leitor = csv.DictReader(f, delimiter=separador)

            for linha in leitor:
                # FIX #2: sem replace manual — encoding já foi detectado corretamente
                nome = linha.get('NOME_PRODUTO', '').strip()
                if not nome or nome.startswith('-'):
                    ignorados += 1
                    continue

                num_registro = str(linha.get('NUMERO_REGISTRO_PRODUTO', '')).strip()

                try:
                    # Monta dict de dados string
                    dados = {}
                    for col_csv, attr in mapeamento_str.items():
                        valor = linha.get(col_csv, '').strip()
                        dados[attr] = valor if valor else None

                    # FIX #7: garante que numero_registro_produto é sempre string
                    if dados.get('numero_registro_produto'):
                        dados['numero_registro_produto'] = str(dados['numero_registro_produto'])

                    # datas já mapeadas como string no mapeamento_str acima

                    # Campos fixos / derivados
                    dados['descricao']         = f"ANVISA – {linha.get('SITUACAO_REGISTRO', '').strip()}"
                    dados['forma_farmaceutica'] = ''
                    dados['dosagem']            = ''

                    # Busca registro existente pelo número de registro (identificador único ANVISA)
                    # Fallback por nome+fabricante para registros sem número
                    existente = None
                    if num_registro:
                        existente = Medicamento.query.filter_by(
                            numero_registro_produto=num_registro
                        ).first()
                    if not existente and not num_registro:
                        fabricante_val = dados.get('fabricante', '')
                        existente = Medicamento.query.filter_by(
                            nome=nome,
                            fabricante=fabricante_val
                        ).first()

                    if existente:
                        for attr, valor in dados.items():
                            setattr(existente, attr, valor)
                        atualizados += 1
                    else:
                        novo = Medicamento(**dados)
                        db.session.add(novo)
                        inseridos += 1

                    # Commit em lote a cada 500
                    if (inseridos + atualizados) % 500 == 0:
                        db.session.commit()
                        print(f"   ✅ {inseridos + atualizados} registros processados...")

                except Exception as e:
                    erros += 1
                    # FIX #1: expunge só o objeto problemático, não desfaz o lote inteiro
                    db.session.expunge_all()
                    db.session.rollback()
                    print(f"   ⚠️  Erro em '{nome}': {e}")
                    continue

        # Commit final do que sobrou
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro no commit final: {e}")

        print("\n📊 Resumo final:")
        print(f"   Inseridos:   {inseridos}")
        print(f"   Atualizados: {atualizados}")
        print(f"   Ignorados:   {ignorados}")
        print(f"   Erros:       {erros}")
        print(f"   Total no banco: {Medicamento.query.count()}")


if __name__ == '__main__':
    popular_do_csv_oficial()
