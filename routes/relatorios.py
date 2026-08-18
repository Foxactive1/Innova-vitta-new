from flask import Blueprint, render_template, request, jsonify, Response
from datetime import datetime, date, timezone
from core.models import db
from core.utils import relatorio_mensal, exportar_dados, tabela_verdade_consulta_normal, tabela_verdade_emergencia

relatorios_bp = Blueprint('relatorios', __name__, url_prefix='/relatorios')

@relatorios_bp.route('/')
def dashboard_relatorios():
    anos = list(range(2024, date.today().year + 2))
    meses = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]
    return render_template('relatorios.html', anos=anos, meses=meses)

@relatorios_bp.route('/mensal')
def relatorio_mensal_view():
    ano = request.args.get('ano', type=int, default=date.today().year)
    mes = request.args.get('mes', type=int, default=date.today().month)
    relatorio = relatorio_mensal(ano, mes)
    return render_template('relatorio_mensal.html', relatorio=relatorio, ano=ano, mes=mes)

@relatorios_bp.route('/api/mensal')
def api_relatorio_mensal():
    ano = request.args.get('ano', type=int, default=date.today().year)
    mes = request.args.get('mes', type=int, default=date.today().month)
    relatorio = relatorio_mensal(ano, mes)
    return jsonify(relatorio)

@relatorios_bp.route('/exportar')
def exportar():
    formato = request.args.get('formato', 'json')
    dados = exportar_dados(formato)
    if formato == 'csv':
        return Response(dados, mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=clinica_dados.csv'})
    else:
        return Response(dados, mimetype='application/json',
                        headers={'Content-Disposition': 'attachment; filename=clinica_dados.json'})

@relatorios_bp.route('/controle-acesso')
def controle_acesso():
    tabela_normal = tabela_verdade_consulta_normal()
    tabela_emergencia = tabela_verdade_emergencia()
    atendidos_normal = sum(1 for r in tabela_normal if r['Atendido'])
    atendidos_emergencia = sum(1 for r in tabela_emergencia if r['Atendido'])
    return render_template('controle_acesso.html',
                           tabela_normal=tabela_normal,
                           tabela_emergencia=tabela_emergencia,
                           atendidos_normal=atendidos_normal,
                           atendidos_emergencia=atendidos_emergencia)