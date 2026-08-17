import json
from datetime import datetime, date, timezone, timedelta
from sqlalchemy import func
from .models import db, Paciente, Atendimento, Consulta, Exame, Pagamento, Receita, Medico

# ============================================================
# FUNÇÕES DE VALIDAÇÃO COMUNS
# ============================================================

def validar_nome(nome):
    """Valida se nome não está vazio."""
    return bool(nome and nome.strip())

def validar_valor(valor_str):
    """Converte string para float com tratamento de vírgula e ponto."""
    if not valor_str:
        return None
    try:
        # Remove pontos de milhar e troca vírgula por ponto
        valor_str = valor_str.replace('.', '').replace(',', '.')
        valor = float(valor_str)
        if valor < 0:
            return None
        return valor
    except ValueError:
        return None

def normalizar_cpf(cpf):
    """Remove pontuação e retorna apenas dígitos, ou None se vazio."""
    if not cpf:
        return None
    cpf = ''.join(filter(str.isdigit, str(cpf)))
    return cpf if cpf else None

def parse_data_hora(data_str, hora_str):
    """Tenta parsear data e hora para datetime com timezone UTC."""
    if not data_str or not hora_str:
        return None
    try:
        dt = datetime.strptime(f'{data_str} {hora_str}', '%Y-%m-%d %H:%M')
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None

def parse_data(data_str):
    """Tenta parsear data para date."""
    if not data_str:
        return None
    try:
        return datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        return None

# ============================================================
# ESTATÍSTICAS GERAIS (sem pandas)
# ============================================================

def estatisticas_gerais():
    """Estatísticas gerais usando SQLAlchemy."""
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

    # Média de idade (calculada via property)
    pacientes = Paciente.query.filter(Paciente.data_nascimento.isnot(None)).all()
    idades = [p.idade for p in pacientes if p.idade is not None]
    media_idade = sum(idades) / len(idades) if idades else 0

    # Top doenças
    doencas_contagem = {}
    for p in Paciente.query.all():
        if p.doencas_previas:
            try:
                doencas = json.loads(p.doencas_previas)
                for d in doencas:
                    doencas_contagem[d] = doencas_contagem.get(d, 0) + 1
            except:
                pass
    top_doencas = dict(sorted(doencas_contagem.items(), key=lambda x: x[1], reverse=True)[:5])

    # Atendimentos por tipo
    tipos = db.session.query(Atendimento.tipo, func.count(Atendimento.id)).group_by(Atendimento.tipo).all()
    atendimentos_por_tipo = {t: c for t, c in tipos}

    # Consultas por mês (últimos 12 meses)
    hoje = date.today()
    inicio = datetime(hoje.year - 1, hoje.month, 1, tzinfo=timezone.utc)
    consultas_mes = db.session.query(
        func.strftime('%Y-%m', Consulta.data_hora).label('mes'),
        func.count(Consulta.id)
    ).filter(Consulta.data_hora >= inicio).group_by('mes').all()
    consultas_por_mes = {c[0]: c[1] for c in consultas_mes}

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
# RELATÓRIO MENSAL – FATURAMENTO UNIFICADO
# ============================================================

def relatorio_mensal(ano=None, mes=None):
    if ano is None:
        ano = date.today().year
    if mes is None:
        mes = date.today().month

    inicio = datetime(ano, mes, 1, tzinfo=timezone.utc)
    if mes == 12:
        fim = datetime(ano + 1, 1, 1, tzinfo=timezone.utc)
    else:
        fim = datetime(ano, mes + 1, 1, tzinfo=timezone.utc)

    # Atendimentos
    atendimentos = Atendimento.query.filter(Atendimento.data >= inicio, Atendimento.data < fim).all()
    total_atendimentos = len(atendimentos)
    atend_por_tipo = {}
    for a in atendimentos:
        atend_por_tipo[a.tipo] = atend_por_tipo.get(a.tipo, 0) + 1

    # Consultas
    consultas = Consulta.query.filter(Consulta.data_hora >= inicio, Consulta.data_hora < fim).all()
    total_consultas = len(consultas)
    consultas_realizadas = sum(1 for c in consultas if c.status == 'realizada')
    consultas_canceladas = sum(1 for c in consultas if c.status == 'cancelada')

    # Exames
    exames = Exame.query.filter(Exame.data >= inicio, Exame.data < fim).all()
    total_exames = len(exames)
    exames_realizados = sum(1 for e in exames if e.status == 'realizado')
    exames_cancelados = sum(1 for e in exames if e.status == 'cancelado')

    # ============================================================
    # FATURAMENTO – SOMA DE TODOS OS PROCEDIMENTOS REALIZADOS
    # (independentemente de pagamentos, para refletir a produção)
    # ============================================================
    # Consultas realizadas
    consultas_realizadas_list = [c for c in consultas if c.status == 'realizada']
    soma_consultas = sum(c.valor or 0 for c in consultas_realizadas_list)

    # Exames realizados
    exames_realizados_list = [e for e in exames if e.status == 'realizado']
    soma_exames = sum(e.valor or 0 for e in exames_realizados_list)

    # Aqui você pode adicionar outros serviços (ex: procedimentos, cirurgias, etc.)
    # basta estender com uma query similar.

    faturamento = soma_consultas + soma_exames

    # (Opcional) Se quiser manter separado o valor recebido via pagamentos,
    # você pode calcular e adicionar como campo extra.
    pagamentos = Pagamento.query.filter(
        Pagamento.data_pagamento.isnot(None),
        Pagamento.data_pagamento >= inicio.date(),
        Pagamento.data_pagamento < fim.date(),
        Pagamento.status == 'pago'
    ).all()
    total_recebido = sum(p.valor or 0 for p in pagamentos)

    # Convertendo para float para consistência
    faturamento = float(faturamento)
    total_recebido = float(total_recebido)

    # Pacientes atendidos únicos
    pacientes_ids = {a.paciente_id for a in atendimentos if a.paciente_id}
    pacientes_atendidos = len(pacientes_ids)

    # Top médicos
    medico_counts = {}
    for a in atendimentos:
        if a.medico_id:
            medico_counts[a.medico_id] = medico_counts.get(a.medico_id, 0) + 1
    top_medicos = []
    for mid, count in sorted(medico_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        medico = Medico.query.get(mid)
        if medico:
            top_medicos.append({'nome': medico.nome, 'atendimentos': count})

    # Receitas
    receitas = Receita.query.filter(Receita.data_emissao >= inicio, Receita.data_emissao < fim).count()

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
        'faturamento': faturamento,           # Valor total dos serviços prestados
        'total_recebido': total_recebido,     # Valor efetivamente pago (se quiser exibir)
        'pacientes_atendidos': pacientes_atendidos,
        'top_medicos': top_medicos,
        'receitas_emitidas': receitas
    }

# ============================================================
# EXPORTAÇÃO DE DADOS (JSON / CSV)
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

    if tipo == 'json':
        return json.dumps(dados, ensure_ascii=False, indent=2)
    elif tipo == 'csv':
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
# CONTROLE DE ACESSO – TABELAS VERDADE
# ============================================================

def verificar_controle_acesso(agendamento, documentos_ok, medico_disponivel, pagamentos_ok, emergencia=False):
    A = agendamento
    B = documentos_ok
    C = medico_disponivel
    D = pagamentos_ok
    if emergencia:
        return C and (B or D)
    else:
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
                        'C∧(B∨D)': atendido,
                        'Atendido': atendido
                    })
    return resultados