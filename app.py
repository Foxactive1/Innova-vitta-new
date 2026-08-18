"""
InNova Vitta+ — Application Factory
Clínica Vida+ | InNovaIdeia Assessoria em Tecnologia
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime, date, timedelta, timezone
from core.models import db, Paciente, Medico, Atendimento, Consulta, Exame, Pagamento, Receita
from routes.pacientes import pacientes_bp
from routes.medicos import medicos_bp
from routes.atendimentos import atendimentos_bp
from routes.consultas import consultas_bp
from routes.exames import exames_bp
from routes.relatorios import relatorios_bp
from routes.receitas import receitas_bp
from routes.servicos import servicos_bp
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config.from_object('config.Config')

# ── Garante pasta instance apenas em ambiente local (SQLite) ───────────────
if not os.environ.get('VERCEL'):
    INSTANCE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
    os.makedirs(INSTANCE_DIR, exist_ok=True)

# ── Inicialização do banco ─────────────────────────────────────────────────
db.init_app(app)

# ── Filtro Jinja2 ──────────────────────────────────────────────────────────
@app.template_filter('load_json')
def load_json_filter(value):
    try:
        return json.loads(value) if value else []
    except Exception:
        return []

# ── Registro de blueprints ─────────────────────────────────────────────────
app.register_blueprint(pacientes_bp)
app.register_blueprint(medicos_bp)
app.register_blueprint(atendimentos_bp)
app.register_blueprint(consultas_bp)
app.register_blueprint(exames_bp)
app.register_blueprint(relatorios_bp)
app.register_blueprint(receitas_bp)
app.register_blueprint(servicos_bp)


# ── Rotas principais ───────────────────────────────────────────────────────
@app.route('/')
def index():
    hoje = date.today()
    now_utc = datetime.now(timezone.utc)

    total_pacientes = Paciente.query.count()
    total_medicos = Medico.query.count()

    consultas_hoje = Consulta.query.filter(
        Consulta.data_hora >= datetime.combine(hoje, datetime.min.time()).replace(tzinfo=timezone.utc),
        Consulta.data_hora <= datetime.combine(hoje, datetime.max.time()).replace(tzinfo=timezone.utc),
        Consulta.status != 'cancelada'
    ).count()

    atendimentos_hoje = Atendimento.query.filter(
        Atendimento.data >= datetime.combine(hoje, datetime.min.time()).replace(tzinfo=timezone.utc),
        Atendimento.data <= datetime.combine(hoje, datetime.max.time()).replace(tzinfo=timezone.utc)
    ).count()

    urgencias = Atendimento.query.filter(Atendimento.tipo.ilike('%urg%')).count()
    consultas_pendentes = Consulta.query.filter(Consulta.status == 'agendada').count()
    exames_pendentes = Exame.query.filter(Exame.status == 'agendado').count()
    pagamentos_atrasados = Pagamento.query.filter(
        Pagamento.data_vencimento < hoje,
        Pagamento.status != 'pago'
    ).count()

    ultimos_atendimentos = Atendimento.query.order_by(Atendimento.data.desc()).limit(5).all()
    proximas_consultas = Consulta.query.filter(
        Consulta.data_hora >= now_utc,
        Consulta.status.in_(['agendada', 'confirmada'])
    ).order_by(Consulta.data_hora.asc()).limit(5).all()

    return render_template('dashboard.html',
                           total_pacientes=total_pacientes,
                           total_medicos=total_medicos,
                           consultas_hoje=consultas_hoje,
                           atendimentos_hoje=atendimentos_hoje,
                           urgencias=urgencias,
                           consultas_pendentes=consultas_pendentes,
                           exames_pendentes=exames_pendentes,
                           pagamentos_atrasados=pagamentos_atrasados,
                           ultimos_atendimentos=ultimos_atendimentos,
                           proximas_consultas=proximas_consultas,
                           now=now_utc)


@app.route('/api/estatisticas')
def api_estatisticas():
    from core.utils import estatisticas_gerais
    return jsonify(estatisticas_gerais())


@app.route('/api/busca-paciente')
def api_busca_paciente():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])
    pacientes = Paciente.query.filter(Paciente.nome.ilike(f'%{q}%')).limit(10).all()
    return jsonify([p.to_dict() for p in pacientes])


@app.route('/api/horarios-disponiveis')
def api_horarios_disponiveis():
    medico_id = request.args.get('medico_id', type=int)
    data_str = request.args.get('data')

    if not medico_id or not data_str:
        return jsonify({'error': 'Parâmetros obrigatórios'}), 400

    try:
        data = datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Data inválida'}), 400

    medico = Medico.query.get_or_404(medico_id)
    ocupados = medico.horarios_ocupados(data)

    todos_horarios = [f"{h:02d}:00" for h in range(8, 19)]
    disponiveis = []

    for h in todos_horarios:
        inicio_h = datetime.strptime(h, '%H:%M').time()
        fim_h = (datetime.combine(date.today(), inicio_h) + timedelta(hours=1)).time()

        conflito = any(
            inicio_h < datetime.strptime(ocup_fim, '%H:%M').time() and
            fim_h > datetime.strptime(ocup_inicio, '%H:%M').time()
            for ocup_inicio, ocup_fim in ocupados
        )

        if not conflito:
            disponiveis.append(h)

    return jsonify({
        'medico': medico.nome,
        'data': data_str,
        'disponiveis': disponiveis,
        'ocupados': ocupados
    })


@app.cli.command("populate-medicamentos")
def populate_command():
    from populate_medicamentos import popular_do_csv_oficial
    popular_do_csv_oficial()


# ── Desenvolvimento local ──────────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
