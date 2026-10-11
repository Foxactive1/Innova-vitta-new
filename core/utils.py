import json
import logging
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo

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

logger = logging.getLogger(__name__)


# ============================================================
# TIMEZONE DA CLÍNICA
# ============================================================

def get_clinic_tz():
    """
    Retorna o timezone configurado para a clínica.

    Lê de config.CLINIC_TIMEZONE (default: America/Sao_Paulo).
    """
    from flask import current_app
    tz_name = current_app.config.get("CLINIC_TIMEZONE", "America/Sao_Paulo")
    return ZoneInfo(tz_name)


def now_clinic():
    """Retorna o datetime atual no timezone da clínica."""
    return datetime.now(get_clinic_tz())


def today_clinic():
    """Retorna a data atual no timezone da clínica."""
    return now_clinic().date()


def utc_to_clinic(dt_utc):
    """Converte um datetime UTC para o timezone da clínica."""
    if dt_utc is None:
        return None
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(get_clinic_tz())


def clinic_to_utc(dt_clinic):
    """Converte um datetime no timezone da clínica para UTC."""
    if dt_clinic is None:
        return None
    if dt_clinic.tzinfo is None:
        dt_clinic = dt_clinic.replace(tzinfo=get_clinic_tz())
    return dt_clinic.astimezone(timezone.utc)


def clinic_day_bounds(d=None):
    """
    Retorna (inicio_utc, fim_utc) para um dia no timezone da clínica.

    Se d=None, usa hoje no timezone da clínica.
    """
    if d is None:
        d = today_clinic()

    tz = get_clinic_tz()
    inicio_local = datetime.combine(d, datetime.min.time(), tzinfo=tz)
    fim_local = datetime.combine(d, datetime.max.time(), tzinfo=tz)

    return (
        inicio_local.astimezone(timezone.utc),
        fim_local.astimezone(timezone.utc),
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

    A data/hora é interpretada no timezone da clínica
    e convertida para UTC antes de ser armazenada.
    """
    if not data_str or not hora_str:
        return None

    try:
        dt_naive = datetime.strptime(
            f'{data_str} {hora_str}',
            '%Y-%m-%d %H:%M'
        )

        # Interpreta no timezone da clínica e converte para UTC
        dt_clinic = dt_naive.replace(tzinfo=get_clinic_tz())
        return dt_clinic.astimezone(timezone.utc)

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
    """Retorna o primeiro instante do mês em UTC (timezone-aware)."""
    return datetime(ano, mes, 1, tzinfo=timezone.utc)


def inicio_proximo_mes(ano, mes):
    """Retorna o primeiro instante do próximo mês em UTC."""
    if mes == 12:
        return datetime(ano + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(ano, mes + 1, 1, tzinfo=timezone.utc)


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

    media_idade = sum(idades) / len(idades) if idades else 0

    # --------------------------------------------------------
    # Top doenças
    # --------------------------------------------------------

    doencas_contagem = {}

    for paciente in Paciente.query.all():
        if not paciente.doencas_previas:
            continue

        try:
            doencas = json.loads(paciente.doencas_previas)

            if isinstance(doencas, list):
                for doenca in doencas:
                    if not doenca:
                        continue
                    doenca = str(doenca).strip()
                    if doenca:
                        doencas_contagem[doenca] = (
                            doencas_contagem.get(doenca, 0) + 1
                        )
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
        .query(Atendimento.tipo, func.count(Atendimento.id))
        .group_by(Atendimento.tipo)
        .all()
    )

    atendimentos_por_tipo = {
        tipo if tipo else 'Não informado': quantidade
        for tipo, quantidade in tipos
    }

    # --------------------------------------------------------
    # Consultas por mês (últimos 12 meses)
    # --------------------------------------------------------

    hoje = today_clinic()

    inicio = datetime(hoje.year - 1, hoje.month, 1, tzinfo=timezone.utc)

    mes_coluna = func.date_trunc('month', Consulta.data_hora).label('mes')

    consultas_mes = (
        db.session
        .query(mes_coluna, func.count(Consulta.id))
        .filter(Consulta.data_hora >= inicio)
        .group_by(mes_coluna)
        .order_by(mes_coluna)
        .all()
    )

    consultas_por_mes = {}

    for mes, quantidade in consultas_mes:
        if mes is None:
            continue
        if hasattr(mes, 'strftime'):
            chave = mes.strftime('%Y-%m')
        else:
            chave = str(mes)[:7]
        consultas_por_mes[chave] = quantidade

    return {
        'media_idade': round(media_idade, 1),
        'total_pacientes': total_pacientes,
        'top_doencas': top_doencas,
        'total_atendimentos': Atendimento.query.count(),
        'total_consultas': Consulta.query.count(),
        'consultas_por_mes': consultas_por_mes,
        'atendimentos_por_tipo': atendimentos_por_tipo
    }


# ============================================================
# RELATÓRIO MENSAL
# FATURAMENTO UNIFICADO
# ============================================================

def relatorio_mensal(ano=None, mes=None):

    if ano is None:
        ano = today_clinic().year

    if mes is None:
        mes = today_clinic().month

    inicio = inicio_mes(ano, mes)
    fim = inicio_proximo_mes(ano, mes)

    # --------------------------------------------------------
    # ATENDIMENTOS
    # --------------------------------------------------------

    atendimentos = (
        Atendimento.query
        .filter(Atendimento.data >= inicio, Atendimento.data < fim)
        .all()
    )

    total_atendimentos = len(atendimentos)

    atend_por_tipo = {}

    for atendimento in atendimentos:
        tipo = atendimento.tipo if atendimento.tipo else 'Não informado'
        atend_por_tipo[tipo] = atend_por_tipo.get(tipo, 0) + 1

    # --------------------------------------------------------
    # CONSULTAS
    # --------------------------------------------------------

    consultas = (
        Consulta.query
        .filter(Consulta.data_hora >= inicio, Consulta.data_hora < fim)
        .all()
    )

    total_consultas = len(consultas)
    consultas_realizadas = sum(1 for c in consultas if c.status == 'realizada')
    consultas_canceladas = sum(1 for c in consultas if c.status == 'cancelada')

    # --------------------------------------------------------
    # EXAMES
    # --------------------------------------------------------

    exames = (
        Exame.query
        .filter(Exame.data >= inicio, Exame.data < fim)
        .all()
    )

    total_exames = len(exames)
    exames_realizados = sum(1 for e in exames if e.status == 'realizado')
    exames_cancelados = sum(1 for e in exames if e.status == 'cancelado')

    # --------------------------------------------------------
    # FATURAMENTO
    # --------------------------------------------------------

    soma_consultas = sum(
        float(c.valor or 0) for c in consultas if c.status == 'realizada'
    )
    soma_exames = sum(
        float(e.valor or 0) for e in exames if e.status == 'realizado'
    )
    faturamento = soma_consultas + soma_exames

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

    total_recebido = sum(float(p.valor or 0) for p in pagamentos)

    # --------------------------------------------------------
    # PACIENTES ATENDIDOS
    # --------------------------------------------------------

    pacientes_ids = {
        a.paciente_id for a in atendimentos if a.paciente_id
    }
    pacientes_atendidos = len(pacientes_ids)

    # --------------------------------------------------------
    # TOP MÉDICOS
    # --------------------------------------------------------

    medico_counts = {}

    for atendimento in atendimentos:
        if atendimento.medico_id:
            medico_counts[atendimento.medico_id] = (
                medico_counts.get(atendimento.medico_id, 0) + 1
            )

    top_medicos = []

    for medico_id, quantidade in sorted(
        medico_counts.items(), key=lambda item: item[1], reverse=True
    )[:5]:
        medico = db.session.get(Medico, medico_id)
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
        .filter(Receita.data_emissao >= inicio, Receita.data_emissao < fim)
        .count()
    )

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
        'faturamento': float(faturamento),
        'total_recebido': float(total_recebido),
        'pacientes_atendidos': pacientes_atendidos,
        'top_medicos': top_medicos,
        'receitas_emitidas': receitas
    }


# ============================================================
# EXPORTAÇÃO DE DADOS
# JSON / CSV
# ============================================================

def exportar_dados(tipo='json'):

    pacientes = [p.to_dict() for p in Paciente.query.all()]
    atendimentos = [a.to_dict() for a in Atendimento.query.all()]
    consultas = [c.to_dict() for c in Consulta.query.all()]
    exames = [e.to_dict() for e in Exame.query.all()]

    dados = {
        'pacientes': pacientes,
        'atendimentos': atendimentos,
        'consultas': consultas,
        'exames': exames,
        'exportado_em': datetime.now(timezone.utc).isoformat()
    }

    if tipo.lower() == 'json':
        return json.dumps(dados, ensure_ascii=False, indent=2, default=str)

    elif tipo.lower() == 'csv':
        import csv
        from io import StringIO

        output = StringIO()

        if pacientes:
            writer = csv.DictWriter(output, fieldnames=pacientes[0].keys())
            writer.writeheader()
            writer.writerows(pacientes)

        return output.getvalue()

    return dados


# ============================================================
# CONTROLE DE ACESSO
# TABELA VERDADE
# ============================================================

def verificar_controle_acesso(
    agendamento, documentos_ok, medico_disponivel,
    pagamentos_ok, emergencia=False
):
    A = bool(agendamento)
    B = bool(documentos_ok)
    C = bool(medico_disponivel)
    D = bool(pagamentos_ok)

    if emergencia:
        return C and (B or D)

    return (A and B and C) or (B and C and D)


def tabela_verdade_consulta_normal():
    resultados = []
    for A in [False, True]:
        for B in [False, True]:
            for C in [False, True]:
                for D in [False, True]:
                    atendido = (A and B and C) or (B and C and D)
                    resultados.append({
                        'A': A, 'B': B, 'C': C, 'D': D,
                        'A∧B∧C': A and B and C,
                        'B∧C∧D': B and C and D,
                        'Atendido': atendido
                    })
    return resultados


def tabela_verdade_emergencia():
    resultados = []
    for A in [False, True]:
        for B in [False, True]:
            for C in [False, True]:
                for D in [False, True]:
                    atendido = C and (B or D)
                    resultados.append({
                        'A': A, 'B': B, 'C': C, 'D': D,
                        'B∨D': B or D,
                        'C∧(B∨D)': C and (B or D),
                        'Atendido': atendido
                    })
    return resultados
