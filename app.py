"""
InNova Vitta+ — Application Factory
Clínica Vida+ | InNovaIdeia Assessoria em Tecnologia
"""

import json
import os
from datetime import date, datetime, timedelta, timezone

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from auth import auth_bp
from core.models import Atendimento, Consulta, Exame, Medico, Paciente, Pagamento, Receita, db
from extensions import csrf, login_manager
from routes.atendimentos import atendimentos_bp
from routes.consultas import consultas_bp
from routes.exames import exames_bp
from routes.medicos import medicos_bp
from routes.pacientes import pacientes_bp
from routes.receitas import receitas_bp
from routes.relatorios import relatorios_bp
from routes.servicos import servicos_bp


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY não configurada. Defina uma chave forte nas variáveis de ambiente."
        )

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para acessar o InNova Vitta+."
    login_manager.login_message_category = "warning"

    app.register_blueprint(auth_bp)
    app.register_blueprint(pacientes_bp)
    app.register_blueprint(medicos_bp)
    app.register_blueprint(atendimentos_bp)
    app.register_blueprint(consultas_bp)
    app.register_blueprint(exames_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(receitas_bp)
    app.register_blueprint(servicos_bp)

    @app.before_request
    def require_authentication():
        allowed = {"auth.login", "static"}
        endpoint = request.endpoint

        if endpoint is None or endpoint in allowed:
            return None

        if current_user.is_authenticated:
            return None

        if request.path.startswith("/api/"):
            return jsonify({"error": "authentication_required"}), 401

        return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'",
        )
        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response

    @app.template_filter("load_json")
    def load_json_filter(value):
        try:
            return json.loads(value) if value else []
        except Exception:
            return []

    @app.context_processor
    def inject_template_context():
        return {"now": datetime.now(timezone.utc)}

    @app.route("/")
    def index():
        hoje = date.today()
        now_utc = datetime.now(timezone.utc)

        inicio_hoje = datetime.combine(hoje, datetime.min.time()).replace(tzinfo=timezone.utc)
        fim_hoje = datetime.combine(hoje, datetime.max.time()).replace(tzinfo=timezone.utc)

        total_pacientes = Paciente.query.count()
        total_medicos = Medico.query.count()

        consultas_hoje = (
            Consulta.query.filter(
                Consulta.data_hora >= inicio_hoje,
                Consulta.data_hora <= fim_hoje,
                Consulta.status != "cancelada",
            ).count()
        )

        atendimentos_hoje = (
            Atendimento.query.filter(
                Atendimento.data >= inicio_hoje,
                Atendimento.data <= fim_hoje,
            ).count()
        )

        urgencias = Atendimento.query.filter(Atendimento.tipo.ilike("%urg%")).count()
        consultas_pendentes = Consulta.query.filter(Consulta.status == "agendada").count()
        exames_pendentes = Exame.query.filter(Exame.status == "agendado").count()

        pagamentos_atrasados = (
            Pagamento.query.filter(
                Pagamento.data_vencimento < hoje,
                Pagamento.status != "pago",
            ).count()
        )

        ultimos_atendimentos = Atendimento.query.order_by(Atendimento.data.desc()).limit(5).all()

        proximas_consultas = (
            Consulta.query.filter(
                Consulta.data_hora >= now_utc,
                Consulta.status.in_(["agendada", "confirmada"]),
            )
            .order_by(Consulta.data_hora.asc())
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
        )

    @app.route("/api/estatisticas")
    def api_estatisticas():
        from core.utils import estatisticas_gerais
        return jsonify(estatisticas_gerais())

    @app.route("/api/busca-paciente")
    def api_busca_paciente():
        q = request.args.get("q", "")
        if len(q) < 2:
            return jsonify([])

        pacientes = (
            Paciente.query.filter(Paciente.nome.ilike(f"%{q}%"))
            .limit(10)
            .all()
        )
        return jsonify([p.to_dict() for p in pacientes])

    @app.route("/api/horarios-disponiveis")
    def api_horarios_disponiveis():
        medico_id = request.args.get("medico_id", type=int)
        data_str = request.args.get("data")

        if not medico_id or not data_str:
            return jsonify({"error": "Parâmetros obrigatórios"}), 400

        try:
            data_consulta = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Data inválida"}), 400

        medico = db.session.get(Medico, medico_id)
        if medico is None:
            return jsonify({"error": "Médico não encontrado"}), 404

        ocupados = medico.horarios_ocupados(data_consulta)
        todos_horarios = [f"{h:02d}:00" for h in range(8, 19)]
        disponiveis = []

        for horario in todos_horarios:
            inicio_h = datetime.strptime(horario, "%H:%M").time()
            fim_h = (
                datetime.combine(date.today(), inicio_h) + timedelta(hours=1)
            ).time()

            conflito = any(
                inicio_h < datetime.strptime(ocup_fim, "%H:%M").time()
                and fim_h > datetime.strptime(ocup_inicio, "%H:%M").time()
                for ocup_inicio, ocup_fim in ocupados
            )

            if not conflito:
                disponiveis.append(horario)

        return jsonify(
            {
                "medico": medico.nome,
                "data": data_str,
                "disponiveis": disponiveis,
                "ocupados": ocupados,
            }
        )

    @app.cli.command("populate-medicamentos")
    def populate_command():
        from populate_medicamentos_neon import popular_do_csv
        popular_do_csv()

    return app


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            print("✅ Banco de dados conectado")
        except Exception as exc:
            print("❌ Erro na conexão com o banco:")
            print(exc)

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=app.config.get("DEBUG", False),
    )
