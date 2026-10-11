"""
Testes unitários para os modelos SQLAlchemy.
"""

from datetime import date, datetime, timezone

from core.models import (
    Paciente, Medico, Servico, Consulta,
    Atendimento, Exame, Pagamento, Receita, Medicamento
)


# ============================================================
# PACIENTE
# ============================================================

class TestPaciente:

    def test_criar_paciente(self, db):
        paciente = Paciente(
            nome="João Silva",
            data_nascimento=date(1990, 5, 15),
            sexo="M",
            telefone="(16) 99999-0000",
            cpf="123.456.789-00"
        )
        db.session.add(paciente)
        db.session.commit()

        assert paciente.id is not None
        assert paciente.nome == "João Silva"

    def test_idade_calculo(self, db):
        hoje = date.today()
        paciente = Paciente(
            nome="Maria",
            data_nascimento=date(hoje.year - 30, hoje.month, hoje.day)
        )
        db.session.add(paciente)
        db.session.commit()

        assert paciente.idade == 30

    def test_idade_sem_data_nascimento(self, db):
        paciente = Paciente(nome="Sem Idade")
        db.session.add(paciente)
        db.session.commit()

        assert paciente.idade is None

    def test_to_dict(self, db):
        paciente = Paciente(
            nome="Teste Dict",
            cpf="111.222.333-44",
            doencas_previas='["diabetes", "hipertensão"]'
        )
        db.session.add(paciente)
        db.session.commit()

        d = paciente.to_dict()
        assert d["nome"] == "Teste Dict"
        assert d["cpf"] == "111.222.333-44"
        assert d["doencas_previas"] == ["diabetes", "hipertensão"]

    def test_to_dict_json_invalido(self, db):
        paciente = Paciente(
            nome="JSON Ruim",
            doencas_previas="json_invalido{{{"
        )
        db.session.add(paciente)
        db.session.commit()

        d = paciente.to_dict()
        assert d["doencas_previas"] == []  # fallback para lista vazia


# ============================================================
# MÉDICO
# ============================================================

class TestMedico:

    def test_criar_medico(self, db):
        medico = Medico(
            nome="Dr. Carlos",
            especialidade="Cardiologia",
            crm="123456-SP"
        )
        db.session.add(medico)
        db.session.commit()

        assert medico.id is not None
        assert medico.ativo is True

    def test_horarios_ocupados(self, db):
        medico = Medico(nome="Dr. Teste", crm="999999-SP")
        db.session.add(medico)
        db.session.commit()

        paciente = Paciente(nome="Paciente Teste")
        db.session.add(paciente)
        db.session.commit()

        consulta = Consulta(
            paciente_id=paciente.id,
            medico_id=medico.id,
            data_hora=datetime(2026, 10, 15, 14, 0, tzinfo=timezone.utc),
            status="agendada"
        )
        db.session.add(consulta)
        db.session.commit()

        ocupados = medico.horarios_ocupados(date(2026, 10, 15))
        assert len(ocupados) == 1
        assert ocupados[0] == ("14:00", "15:00")

    def test_horarios_ocupados_cancelada_nao_conta(self, db):
        medico = Medico(nome="Dr. Cancel", crm="888888-SP")
        db.session.add(medico)
        db.session.commit()

        paciente = Paciente(nome="Paciente Cancel")
        db.session.add(paciente)
        db.session.commit()

        consulta = Consulta(
            paciente_id=paciente.id,
            medico_id=medico.id,
            data_hora=datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc),
            status="cancelada"
        )
        db.session.add(consulta)
        db.session.commit()

        ocupados = medico.horarios_ocupados(date(2026, 10, 15))
        assert len(ocupados) == 0


# ============================================================
# SERVIÇO
# ============================================================

class TestServico:

    def test_criar_servico(self, db):
        servico = Servico(
            nome="Consulta Cardiologia",
            categoria="consulta",
            valor=250.00
        )
        db.session.add(servico)
        db.session.commit()

        assert servico.id is not None
        assert float(servico.valor) == 250.00

    def test_to_dict_valor_none(self, db):
        servico = Servico(nome="Teste", categoria="consulta", valor=None)
        db.session.add(servico)
        db.session.commit()

        d = servico.to_dict()
        assert d["valor"] == 0.0


# ============================================================
# CONSULTA
# ============================================================

class TestConsulta:

    def _setup(self, db):
        paciente = Paciente(nome="Paciente Consulta")
        medico = Medico(nome="Dr. Consulta", crm="777777-SP")
        servico = Servico(nome="Consulta Geral", categoria="consulta", valor=150.00)
        db.session.add_all([paciente, medico, servico])
        db.session.commit()
        return paciente, medico, servico

    def test_criar_consulta(self, db):
        paciente, medico, servico = self._setup(db)

        consulta = Consulta(
            paciente_id=paciente.id,
            medico_id=medico.id,
            servico_id=servico.id,
            data_hora=datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc),
            status="agendada",
            valor=servico.valor
        )
        db.session.add(consulta)
        db.session.commit()

        assert consulta.id is not None
        assert consulta.status == "agendada"

    def test_to_dict_com_relacionamentos(self, db):
        paciente, medico, servico = self._setup(db)

        consulta = Consulta(
            paciente_id=paciente.id,
            medico_id=medico.id,
            servico_id=servico.id,
            data_hora=datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc),
            valor=150.00
        )
        db.session.add(consulta)
        db.session.commit()

        d = consulta.to_dict()
        assert d["paciente"]["nome"] == "Paciente Consulta"
        assert d["medico"]["nome"] == "Dr. Consulta"
        assert d["servico"]["nome"] == "Consulta Geral"


# ============================================================
# ATENDIMENTO
# ============================================================

class TestAtendimento:

    def test_criar_atendimento(self, db):
        paciente = Paciente(nome="Paciente Atendimento")
        medico = Medico(nome="Dr. Atendimento", crm="666666-SP")
        db.session.add_all([paciente, medico])
        db.session.commit()

        atendimento = Atendimento(
            paciente_id=paciente.id,
            medico_id=medico.id,
            tipo="consulta",
            sintomas='["febre", "tosse"]',
            diagnostico="Gripe",
            data=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
        )
        db.session.add(atendimento)
        db.session.commit()

        assert atendimento.id is not None

        d = atendimento.to_dict()
        assert d["sintomas"] == ["febre", "tosse"]
        assert d["diagnostico"] == "Gripe"


# ============================================================
# PAGAMENTO
# ============================================================

class TestPagamento:

    def test_criar_pagamento(self, db):
        paciente = Paciente(nome="Paciente Pagamento")
        db.session.add(paciente)
        db.session.commit()

        pagamento = Pagamento(
            paciente_id=paciente.id,
            descricao="Consulta",
            valor=200.00,
            data_vencimento=date(2026, 10, 20),
            status="pendente"
        )
        db.session.add(pagamento)
        db.session.commit()

        assert pagamento.id is not None
        assert pagamento.status == "pendente"


# ============================================================
# RECEITA
# ============================================================

class TestReceita:

    def test_criar_receita(self, db):
        paciente = Paciente(nome="Paciente Receita")
        medico = Medico(nome="Dr. Receita", crm="555555-SP")
        db.session.add_all([paciente, medico])
        db.session.commit()

        receita = Receita(
            paciente_id=paciente.id,
            medico_id=medico.id,
            medicamentos='[{"nome": "Paracetamol", "dose": "500mg"}]',
            observacoes="Tomar 2x ao dia"
        )
        db.session.add(receita)
        db.session.commit()

        d = receita.to_dict()
        assert d["medicamentos"] == [{"nome": "Paracetamol", "dose": "500mg"}]


# ============================================================
# MEDICAMENTO
# ============================================================

class TestMedicamento:

    def test_criar_medicamento(self, db):
        medicamento = Medicamento(
            nome="Paracetamol 500mg",
            principio_ativo="Paracetamol",
            dosagem="500mg",
            forma_farmaceutica="Comprimido",
            numero_registro_produto="REG-001"
        )
        db.session.add(medicamento)
        db.session.commit()

        assert medicamento.id is not None
        assert medicamento.nome == "Paracetamol 500mg"
