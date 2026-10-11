"""
Testes de integração para as rotas principais.
"""

from datetime import date, datetime, timedelta, timezone


# ============================================================
# AUTENTICAÇÃO
# ============================================================

class TestAutenticacao:

    def test_dashboard_redireciona_sem_login(self, client):
        response = client.get("/")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_api_retorna_401_sem_login(self, client):
        response = client.get("/api/estatisticas")
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "authentication_required"


# ============================================================
# APIs PÚBLICAS (sem auth para facilitar testes)
# ============================================================

class TestAPIs:

    def _auth_headers(self, client, app, db):
        """
        Cria um usuário admin e faz login.
        """
        from core.models import Usuario

        usuario = Usuario(
            username="admin_test",
            role="admin"
        )
        usuario.set_password("senha123")
        db.session.add(usuario)
        db.session.commit()

        # Faz login via rota de auth
        response = client.post("/login", data={
            "username": "admin_test",
            "password": "senha123"
        }, follow_redirects=True)

        return response

    def test_busca_paciente_curta(self, client, app, db):
        """Busca com menos de 2 caracteres retorna lista vazia."""
        response = client.get("/api/busca-paciente?q=a")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_busca_paciente_encontra(self, client, app, db):
        from core.models import Paciente

        paciente = Paciente(nome="Carlos Teste Silva")
        db.session.add(paciente)
        db.session.commit()

        response = client.get("/api/busca-paciente?q=Carlos")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["nome"] == "Carlos Teste Silva"

    def test_horarios_disponiveis_sem_parametros(self, client):
        response = client.get("/api/horarios-disponiveis")
        assert response.status_code == 400

    def test_horarios_disponiveis_medico_inexistente(self, client):
        response = client.get(
            "/api/horarios-disponiveis?medico_id=999&data=2026-10-15"
        )
        assert response.status_code == 404

    def test_horarios_disponiveis_sucesso(self, client, app, db):
        from core.models import Medico, Paciente, Consulta

        medico = Medico(nome="Dr. Horário", crm="444444-SP")
        paciente = Paciente(nome="Paciente Horário")
        db.session.add_all([medico, paciente])
        db.session.commit()

        # Cria consulta às 14h
        consulta = Consulta(
            paciente_id=paciente.id,
            medico_id=medico.id,
            data_hora=datetime(2026, 10, 15, 14, 0, tzinfo=timezone.utc),
            status="agendada"
        )
        db.session.add(consulta)
        db.session.commit()

        response = client.get(
            f"/api/horarios-disponiveis?medico_id={medico.id}&data=2026-10-15"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert "disponiveis" in data
        assert "ocupados" in data
        assert "14:00" not in data["disponiveis"]
        assert ("14:00", "15:00") in data["ocupados"]


# ============================================================
# CONFLITO DE HORÁRIO
# ============================================================

class TestConflitoHorario:

    def test_conflito_detectado(self, app, db):
        """Duas consultas no mesmo horário para o mesmo médico."""
        from core.models import Medico, Paciente, Consulta

        medico = Medico(nome="Dr. Conflito", crm="333333-SP")
        p1 = Paciente(nome="Paciente 1")
        p2 = Paciente(nome="Paciente 2")
        db.session.add_all([medico, p1, p2])
        db.session.commit()

        horario = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)

        c1 = Consulta(
            paciente_id=p1.id,
            medico_id=medico.id,
            data_hora=horario,
            status="agendada"
        )
        db.session.add(c1)
        db.session.commit()

        # Tenta criar consulta sobreposta (9:30 → 10:30, overlap com 10:00)
        fim_c1 = horario + timedelta(hours=1)
        inicio_c2 = horario - timedelta(minutes=30)
        fim_c2 = inicio_c2 + timedelta(hours=1)

        conflito = Consulta.query.filter(
            Consulta.medico_id == medico.id,
            Consulta.status != "cancelada",
            Consulta.data_hora < fim_c2,
            Consulta.data_hora + timedelta(hours=1) > inicio_c2
        ).first()

        assert conflito is not None
        assert conflito.id == c1.id

    def test_sem_conflito_horarios_separados(self, app, db):
        """Consultas em horários distintos não geram conflito."""
        from core.models import Medico, Paciente, Consulta

        medico = Medico(nome="Dr. Sem Conflito", crm="222222-SP")
        p1 = Paciente(nome="Paciente A")
        p2 = Paciente(nome="Paciente B")
        db.session.add_all([medico, p1, p2])
        db.session.commit()

        c1 = Consulta(
            paciente_id=p1.id,
            medico_id=medico.id,
            data_hora=datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc),
            status="agendada"
        )
        db.session.add(c1)
        db.session.commit()

        # Consulta às 10h — sem overlap com 8h-9h
        inicio_c2 = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)
        fim_c2 = inicio_c2 + timedelta(hours=1)

        conflito = Consulta.query.filter(
            Consulta.medico_id == medico.id,
            Consulta.status != "cancelada",
            Consulta.data_hora < fim_c2,
            Consulta.data_hora + timedelta(hours=1) > inicio_c2
        ).first()

        assert conflito is None

    def test_consulta_cancelada_nao_conflita(self, app, db):
        """Consulta cancelada não bloqueia o horário."""
        from core.models import Medico, Paciente, Consulta

        medico = Medico(nome="Dr. Cancelado", crm="111111-SP")
        p1 = Paciente(nome="Paciente X")
        db.session.add_all([medico, p1])
        db.session.commit()

        horario = datetime(2026, 10, 20, 14, 0, tzinfo=timezone.utc)

        c1 = Consulta(
            paciente_id=p1.id,
            medico_id=medico.id,
            data_hora=horario,
            status="cancelada"
        )
        db.session.add(c1)
        db.session.commit()

        fim_c2 = horario + timedelta(hours=1)

        conflito = Consulta.query.filter(
            Consulta.medico_id == medico.id,
            Consulta.status != "cancelada",
            Consulta.data_hora < fim_c2,
            Consulta.data_hora + timedelta(hours=1) > horario
        ).first()

        assert conflito is None
