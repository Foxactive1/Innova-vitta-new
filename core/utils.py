import json
from datetime import datetime, date, timezone, timedelta

from sqlalchemy import func

from .models import (
    db,
    Paciente,
    Atendimento,
    Consulta,
    Exame,
    Pagamento,
    Receita,
    Medico
)


# ============================================================
# FUNÇÕES DE VALIDAÇÃO COMUNS
# ============================================================

def validar_nome(nome):
    """Valida se o nome não está vazio."""
    return bool(nome and str(nome).strip())


def validar_valor(valor_str):
    """
    Converte valor para float.

    Aceita:
        100
        100.50
        100,50
        1.000,50
    """
    if valor_str is None or valor_str == '':
        return None

    try:
        valor_str = str(valor_str).strip()

        # Formato brasileiro: 1.000,50
        if ',' in valor_str:
            valor_str = valor_str.replace('.', '')
            valor_str = valor_str.replace(',', '.')

        valor = float(valor_str)

        if valor < 0:
            return None

        return valor

    except (ValueError, TypeError):
        return None


def normalizar_cpf(cpf):
    """Remove pontuação e retorna somente números."""
    if not cpf:
        return None

    cpf = ''.join(filter(str.isdigit, str(cpf)))

    return cpf if cpf else None


def parse_data_hora(data_str, hora_str):
    """
    Converte data + hora para datetime UTC.

    Esperado:
        data_str = YYYY-MM-DD
        hora_str = HH:MM
    """
    if not data_str or not hora_str:
        return None

    try:
        dt = datetime.strptime(
            f'{data_str} {hora_str}',
            '%Y-%m-%d %H:%M'
        )

        return dt.replace(tzinfo=timezone.utc)

    except (ValueError, TypeError):
        return None


def parse_data(data_str):
    """Converte string YYYY-MM-DD para date."""
    if not data_str:
        return None

    try:
        return datetime.strptime(
            str(data_str),
            '%Y-%m-%d'
        ).date()

    except (ValueError, TypeError):
        return None


# ============================================================
# AUXILIAR — CONVERSÃO SEGURA DE DATA
# ============================================================

def inicio_mes(ano, mes):
    """Retorna o primeiro instante do mês em UTC."""
    return datetime(
        ano,
        mes,
        1,
        tzinfo=timezone.utc
    )


def inicio_proximo_mes(ano, mes):
    """Retorna o primeiro instante do próximo mês em UTC."""
    if mes == 12:
        return datetime(
            ano + 1,
            1,
            1,
            tzinfo=timezone.utc
        )

    return datetime(
        ano,
        mes + 1,
        1,
        tzinfo=timezone.utc
    )


# ============================================================
# ESTATÍSTICAS GERAIS
# COMPATÍVEL COM POSTGRESQL / NEON
# ============================================================

def estatisticas_gerais():
    """
    Retorna estatísticas gerais da clínica.

    Compatível com PostgreSQL/Neon.

    A consulta mensal utiliza date_trunc(),
    evitando funções específicas do SQLite como strftime().
    """

    total_pacientes = Paciente.query.count()

    # --------------------------------------------------------
    # Sem pacientes
    # --------------------------------------------------------

    if total_pacientes == 0:
        return {
            'media_idade': 0,
            'total_pacientes': 0,
            'top_doencas': {},
            'total_atendimentos': 0,
            'total_consultas': 0,
            'consultas_por_mes': {},
            'atendimentos_por_tipo': {}
        }

    # --------------------------------------------------------
    # Média de idade
    # --------------------------------------------------------

    pacientes = Paciente.query.filter(
        Paciente.data_nascimento.isnot(None)
    ).all()

    idades = []

    for paciente in pacientes:
        try:
            idade = paciente.idade

            if idade is not None:
                idades.append(idade)

        except Exception:
            continue

    media_idade = (
        sum(idades) / len(idades)
        if idades
        else 0
    )

    # --------------------------------------------------------
    # Top doenças
    # --------------------------------------------------------

    doencas_contagem = {}

    pacientes_com_dados = Paciente.query.all()

    for paciente in pacientes_com_dados:

        if not paciente.doencas_previas:
            continue

        try:
            doencas = json.loads(
                paciente.doencas_previas
            )

            # Caso seja uma lista
            if isinstance(doencas, list):

                for doenca in doencas:

                    if not doenca:
                        continue

                    doenca = str(doenca).strip()

                    if doenca:
                        doencas_contagem[doenca] = (
                            doencas_contagem.get(doenca, 0) + 1
                        )

            # Caso seja uma string
            elif isinstance(doencas, str):

                doenca = doencas.strip()

                if doenca:
                    doencas_contagem[doenca] = (
                        doencas_contagem.get(doenca, 0) + 1
                    )

        except (json.JSONDecodeError, TypeError):
            continue

    top_doencas = dict(
        sorted(
            doencas_contagem.items(),
            key=lambda item: item[1],
            reverse=True
        )[:5]
    )

    # --------------------------------------------------------
    # Atendimentos por tipo
    # --------------------------------------------------------

    tipos = (
        db.session
        .query(
            Atendimento.tipo,
            func.count(Atendimento.id)
        )
        .group_by(Atendimento.tipo)
        .all()
    )

    atendimentos_por_tipo = {
        tipo if tipo else 'Não informado': quantidade
        for tipo, quantidade in tipos
    }

    # --------------------------------------------------------
    # Consultas por mês
    # PostgreSQL / Neon
    # --------------------------------------------------------

    hoje = date.today()

    inicio = datetime(
        hoje.year - 1,
        hoje.month,
        1,
        tzinfo=timezone.utc
    )

    # PostgreSQL:
    # date_trunc('month', timestamp)
    #
    # Em vez de:
    # strftime('%Y-%m', ...)
    #
    mes_coluna = func.date_trunc(
        'month',
        Consulta.data_hora
    ).label('mes')

    consultas_mes = (
        db.session
        .query(
            mes_coluna,
            func.count(Consulta.id)
        )
        .filter(
            Consulta.data_hora >= inicio
        )
        .group_by(mes_coluna)
        .order_by(mes_coluna)
        .all()
    )

    consultas_por_mes = {}

    for mes, quantidade in consultas_mes:

        if mes is None:
            continue

        # PostgreSQL retorna datetime
        if hasattr(mes, 'strftime'):
            chave = mes.strftime('%Y-%m')
        else:
            chave = str(mes)[:7]

        consultas_por_mes[chave] = quantidade

    # --------------------------------------------------------
    # Resultado
    # --------------------------------------------------------

    return {
        'media_idade': round(media_idade, 1),

        'total_pacientes': total_pacientes,

        'top_doencas': top_doencas,

        'total_atendimentos': (
            Atendimento.query.count()
        ),

        'total_consultas': (
            Consulta.query.count()
        ),

        'consultas_por_mes': consultas_por_mes,

        'atendimentos_por_tipo': (
            atendimentos_por_tipo
        )
    }


# ============================================================
# RELATÓRIO MENSAL
# FATURAMENTO UNIFICADO
# ============================================================

def relatorio_mensal(ano=None, mes=None):

    if ano is None:
        ano = date.today().year

    if mes is None:
        mes = date.today().month

    # --------------------------------------------------------
    # Período
    # --------------------------------------------------------

    inicio = inicio_mes(ano, mes)

    fim = inicio_proximo_mes(ano, mes)

    # --------------------------------------------------------
    # ATENDIMENTOS
    # --------------------------------------------------------

    atendimentos = (
        Atendimento.query
        .filter(
            Atendimento.data >= inicio,
            Atendimento.data < fim
        )
        .all()
    )

    total_atendimentos = len(atendimentos)

    atend_por_tipo = {}

    for atendimento in atendimentos:

        tipo = (
            atendimento.tipo
            if atendimento.tipo
            else 'Não informado'
        )

        atend_por_tipo[tipo] = (
            atend_por_tipo.get(tipo, 0) + 1
        )

    # --------------------------------------------------------
    # CONSULTAS
    # --------------------------------------------------------

    consultas = (
        Consulta.query
        .filter(
            Consulta.data_hora >= inicio,
            Consulta.data_hora < fim
        )
        .all()
    )

    total_consultas = len(consultas)

    consultas_realizadas = sum(
        1
        for consulta in consultas
        if consulta.status == 'realizada'
    )

    consultas_canceladas = sum(
        1
        for consulta in consultas
        if consulta.status == 'cancelada'
    )

    # --------------------------------------------------------
    # EXAMES
    # --------------------------------------------------------

    exames = (
        Exame.query
        .filter(
            Exame.data >= inicio,
            Exame.data < fim
        )
        .all()
    )

    total_exames = len(exames)

    exames_realizados = sum(
        1
        for exame in exames
        if exame.status == 'realizado'
    )

    exames_cancelados = sum(
        1
        for exame in exames
        if exame.status == 'cancelado'
    )

    # --------------------------------------------------------
    # FATURAMENTO
    # --------------------------------------------------------

    soma_consultas = sum(
        float(consulta.valor or 0)
        for consulta in consultas
        if consulta.status == 'realizada'
    )

    soma_exames = sum(
        float(exame.valor or 0)
        for exame in exames
        if exame.status == 'realizado'
    )

    faturamento = (
        soma_consultas +
        soma_exames
    )

    # --------------------------------------------------------
    # PAGAMENTOS RECEBIDOS
    # --------------------------------------------------------

    pagamentos = (
        Pagamento.query
        .filter(
            Pagamento.data_pagamento.isnot(None),
            Pagamento.data_pagamento >= inicio.date(),
            Pagamento.data_pagamento < fim.date(),
            Pagamento.status == 'pago'
        )
        .all()
    )

    total_recebido = sum(
        float(pagamento.valor or 0)
        for pagamento in pagamentos
    )

    # --------------------------------------------------------
    # PACIENTES ATENDIDOS
    # --------------------------------------------------------

    pacientes_ids = {
        atendimento.paciente_id
        for atendimento in atendimentos
        if atendimento.paciente_id
    }

    pacientes_atendidos = len(pacientes_ids)

    # --------------------------------------------------------
    # TOP MÉDICOS
    # --------------------------------------------------------

    medico_counts = {}

    for atendimento in atendimentos:

        if atendimento.medico_id:

            medico_counts[atendimento.medico_id] = (
                medico_counts.get(
                    atendimento.medico_id,
                    0
                ) + 1
            )

    top_medicos = []

    for medico_id, quantidade in sorted(
        medico_counts.items(),
        key=lambda item: item[1],
        reverse=True
    )[:5]:

        medico = db.session.get(
            Medico,
            medico_id
        )

        if medico:

            top_medicos.append({
                'nome': medico.nome,
                'atendimentos': quantidade
            })

    # --------------------------------------------------------
    # RECEITAS
    # --------------------------------------------------------

    receitas = (
        Receita.query
        .filter(
            Receita.data_emissao >= inicio,
            Receita.data_emissao < fim
        )
        .count()
    )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    return {

        'periodo': f'{ano}-{mes:02d}',

        'atendimentos': {
            'total': total_atendimentos,
            'por_tipo': atend_por_tipo
        },

        'consultas': {
            'total': total_consultas,
            'realizadas': consultas_realizadas,
            'canceladas': consultas_canceladas
        },

        'exames': {
            'total': total_exames,
            'realizados': exames_realizados,
            'cancelados': exames_cancelados
        },

        'faturamento': float(
            faturamento
        ),

        'total_recebido': float(
            total_recebido
        ),

        'pacientes_atendidos': (
            pacientes_atendidos
        ),

        'top_medicos': top_medicos,

        'receitas_emitidas': receitas
    }


# ============================================================
# EXPORTAÇÃO DE DADOS
# JSON / CSV
# ============================================================

def exportar_dados(tipo='json'):

    pacientes = [
        paciente.to_dict()
        for paciente in Paciente.query.all()
    ]

    atendimentos = [
        atendimento.to_dict()
        for atendimento in Atendimento.query.all()
    ]

    consultas = [
        consulta.to_dict()
        for consulta in Consulta.query.all()
    ]

    exames = [
        exame.to_dict()
        for exame in Exame.query.all()
    ]

    dados = {

        'pacientes': pacientes,

        'atendimentos': atendimentos,

        'consultas': consultas,

        'exames': exames,

        'exportado_em': (
            datetime
            .now(timezone.utc)
            .isoformat()
        )
    }

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    if tipo.lower() == 'json':

        return json.dumps(
            dados,
            ensure_ascii=False,
            indent=2,
            default=str
        )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    elif tipo.lower() == 'csv':

        import csv
        from io import StringIO

        output = StringIO()

        if pacientes:

            writer = csv.DictWriter(
                output,
                fieldnames=pacientes[0].keys()
            )

            writer.writeheader()

            writer.writerows(
                pacientes
            )

        return output.getvalue()

    return dados


# ============================================================
# CONTROLE DE ACESSO
# TABELA VERDADE
# ============================================================

def verificar_controle_acesso(
    agendamento,
    documentos_ok,
    medico_disponivel,
    pagamentos_ok,
    emergencia=False
):

    A = bool(agendamento)
    B = bool(documentos_ok)
    C = bool(medico_disponivel)
    D = bool(pagamentos_ok)

    # --------------------------------------------------------
    # EMERGÊNCIA
    # --------------------------------------------------------

    if emergencia:

        return C and (B or D)

    # --------------------------------------------------------
    # CONSULTA NORMAL
    # --------------------------------------------------------

    return (
        (A and B and C)
        or
        (B and C and D)
    )


# ============================================================
# TABELA VERDADE — CONSULTA NORMAL
# ============================================================

def tabela_verdade_consulta_normal():

    resultados = []

    for A in [False, True]:

        for B in [False, True]:

            for C in [False, True]:

                for D in [False, True]:

                    atendido = (
                        (A and B and C)
                        or
                        (B and C and D)
                    )

                    resultados.append({

                        'A': A,

                        'B': B,

                        'C': C,

                        'D': D,

                        'A∧B∧C': (
                            A and B and C
                        ),

                        'B∧C∧D': (
                            B and C and D
                        ),

                        'Atendido': atendido
                    })

    return resultados


# ============================================================
# TABELA VERDADE — EMERGÊNCIA
# ============================================================

def tabela_verdade_emergencia():

    resultados = []

    for A in [False, True]:

        for B in [False, True]:

            for C in [False, True]:

                for D in [False, True]:

                    atendido = (
                        C and (B or D)
                    )

                    resultados.append({

                        'A': A,

                        'B': B,

                        'C': C,

                        'D': D,

                        'B∨D': (
                            B or D
                        ),

                        'C∧(B∨D)': (
                            C and (B or D)
                        ),

                        'Atendido': atendido
                    })

    return resultados