"""
InNova Vitta+ — Application Factory
Clínica Vida+ | InNovaIdeia Assessoria em Tecnologia
"""

import os
import json

from datetime import datetime, date, timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

# ============================================================
# CARREGAMENTO DO AMBIENTE
# ============================================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# .env1 contém a configuração atual do PostgreSQL/Neon
ENV_FILE = os.path.join(BASE_DIR, ".env1")

if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)
else:
    # Fallback para .env, caso exista
    load_dotenv(os.path.join(BASE_DIR, ".env"))


# ============================================================
# MODELOS
# ============================================================

from core.models import (
    db,
    Paciente,
    Medico,
    Atendimento,
    Consulta,
    Exame,
    Pagamento,
    Receita,
)


# ============================================================
# BLUEPRINTS
# ============================================================

from routes.pacientes import pacientes_bp
from routes.medicos import medicos_bp
from routes.atendimentos import atendimentos_bp
from routes.consultas import consultas_bp
from routes.exames import exames_bp
from routes.relatorios import relatorios_bp
from routes.receitas import receitas_bp
from routes.servicos import servicos_bp


# ============================================================
# APPLICATION
# ============================================================

app = Flask(__name__)

app.config.from_object("config.Config")


# ============================================================
# INFORMAÇÕES DO BANCO
# ============================================================

DATABASE_URL = app.config.get(
    "SQLALCHEMY_DATABASE_URI",
    ""
)

if DATABASE_URL.startswith(("postgresql://", "postgres://")):
    print("\n======================================")
    print(" INNOVA VITTA+")
    print(" BANCO: POSTGRESQL / NEON")
    print("======================================")

elif DATABASE_URL.startswith("sqlite"):
    print("\n======================================")
    print(" INNOVA VITTA+")
    print(" BANCO: SQLITE LOCAL")
    print("======================================")

else:
    print("\n⚠️ Banco de dados não identificado.")


# ============================================================
# INSTANCE
# ============================================================

# Mantém a pasta instance para arquivos locais,
# mas ela NÃO será usada pelo banco quando DATABASE_URL
# estiver apontando para o Neon.

INSTANCE_DIR = os.path.join(
    BASE_DIR,
    "instance"
)

os.makedirs(
    INSTANCE_DIR,
    exist_ok=True
)


# ============================================================
# SQLALCHEMY
# ============================================================

db.init_app(app)


# ============================================================
# FILTRO JINJA2
# ============================================================

@app.template_filter("load_json")
def load_json_filter(value):

    try:
        return json.loads(value) if value else []

    except Exception:
        return []


# ============================================================
# BLUEPRINTS
# ============================================================

app.register_blueprint(pacientes_bp)
app.register_blueprint(medicos_bp)
app.register_blueprint(atendimentos_bp)
app.register_blueprint(consultas_bp)
app.register_blueprint(exames_bp)
app.register_blueprint(relatorios_bp)
app.register_blueprint(receitas_bp)
app.register_blueprint(servicos_bp)


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
def index():

    hoje = date.today()

    now_utc = datetime.now(timezone.utc)

    inicio_hoje = datetime.combine(
        hoje,
        datetime.min.time()
    ).replace(
        tzinfo=timezone.utc
    )

    fim_hoje = datetime.combine(
        hoje,
        datetime.max.time()
    ).replace(
        tzinfo=timezone.utc
    )

    total_pacientes = (
        Paciente.query.count()
    )

    total_medicos = (
        Medico.query.count()
    )

    consultas_hoje = (
        Consulta.query
        .filter(
            Consulta.data_hora >= inicio_hoje,
            Consulta.data_hora <= fim_hoje,
            Consulta.status != "cancelada"
        )
        .count()
    )

    atendimentos_hoje = (
        Atendimento.query
        .filter(
            Atendimento.data >= inicio_hoje,
            Atendimento.data <= fim_hoje
        )
        .count()
    )

    urgencias = (
        Atendimento.query
        .filter(
            Atendimento.tipo.ilike("%urg%")
        )
        .count()
    )

    consultas_pendentes = (
        Consulta.query
        .filter(
            Consulta.status == "agendada"
        )
        .count()
    )

    exames_pendentes = (
        Exame.query
        .filter(
            Exame.status == "agendado"
        )
        .count()
    )

    pagamentos_atrasados = (
        Pagamento.query
        .filter(
            Pagamento.data_vencimento < hoje,
            Pagamento.status != "pago"
        )
        .count()
    )

    ultimos_atendimentos = (
        Atendimento.query
        .order_by(
            Atendimento.data.desc()
        )
        .limit(5)
        .all()
    )

    proximas_consultas = (
        Consulta.query
        .filter(
            Consulta.data_hora >= now_utc,
            Consulta.status.in_(
                ["agendada", "confirmada"]
            )
        )
        .order_by(
            Consulta.data_hora.asc()
        )
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",

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
        now=now_utc
    )


# ============================================================
# API ESTATÍSTICAS
# ============================================================

@app.route("/api/estatisticas")
def api_estatisticas():

    from core.utils import estatisticas_gerais

    return jsonify(
        estatisticas_gerais()
    )


# ============================================================
# API BUSCA PACIENTE
# ============================================================

@app.route("/api/busca-paciente")
def api_busca_paciente():

    q = request.args.get(
        "q",
        ""
    )

    if len(q) < 2:
        return jsonify([])

    pacientes = (
        Paciente.query
        .filter(
            Paciente.nome.ilike(
                f"%{q}%"
            )
        )
        .limit(10)
        .all()
    )

    return jsonify([
        p.to_dict()
        for p in pacientes
    ])


# ============================================================
# API HORÁRIOS DISPONÍVEIS
# ============================================================

@app.route("/api/horarios-disponiveis")
def api_horarios_disponiveis():

    medico_id = request.args.get(
        "medico_id",
        type=int
    )

    data_str = request.args.get(
        "data"
    )

    if not medico_id or not data_str:

        return jsonify({
            "error": "Parâmetros obrigatórios"
        }), 400

    try:

        data = datetime.strptime(
            data_str,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        return jsonify({
            "error": "Data inválida"
        }), 400

    medico = Medico.query.get_or_404(
        medico_id
    )

    ocupados = medico.horarios_ocupados(
        data
    )

    todos_horarios = [
        f"{h:02d}:00"
        for h in range(8, 19)
    ]

    disponiveis = []

    for h in todos_horarios:

        inicio_h = datetime.strptime(
            h,
            "%H:%M"
        ).time()

        fim_h = (
            datetime.combine(
                date.today(),
                inicio_h
            )
            + timedelta(hours=1)
        ).time()

        conflito = any(

            inicio_h <
            datetime.strptime(
                ocup_fim,
                "%H:%M"
            ).time()

            and

            fim_h >
            datetime.strptime(
                ocup_inicio,
                "%H:%M"
            ).time()

            for ocup_inicio, ocup_fim
            in ocupados
        )

        if not conflito:
            disponiveis.append(h)

    return jsonify({

        "medico": medico.nome,

        "data": data_str,

        "disponiveis": disponiveis,

        "ocupados": ocupados
    })


# ============================================================
# CLI — POPULAR MEDICAMENTOS
# ============================================================

@app.cli.command(
    "populate-medicamentos"
)
def populate_command():

    from populate_medicamentos_neon import (
        popular_do_csv
    )

    popular_do_csv()


# ============================================================
# DESENVOLVIMENTO
# ============================================================

if __name__ == "__main__":

    # IMPORTANTE:
    # Não executar db.create_all() aqui.
    #
    # O schema do Neon já existe e foi validado.
    #
    # O SQLAlchemy deve trabalhar sobre as tabelas existentes.

    print("\n======================================")
    print(" InNova Vitta+ iniciado")
    print("======================================")

    with app.app_context():

        try:

            with db.engine.connect() as conn:

                conn.exec_driver_sql(
                    "SELECT 1"
                )

            print(
                "✅ PostgreSQL/Neon conectado"
            )

        except Exception as e:

            print(
                "❌ Erro na conexão com o banco:"
            )

            print(e)

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=app.config.get(
            "DEBUG",
            False
        )
    )