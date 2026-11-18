from flask import Flask, g
import pytest
import os

from core.models import Atendimento, ClinicMembership, Paciente, Tenant, User, db
from core.tenancy import _scope_queries_to_active_tenant  # registers ORM hooks
from auth.permissions import role_allowed


def test_tenant_scope_hides_records_from_other_clinics():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI=os.environ.get("TEST_DATABASE_URL", "sqlite://"), SQLALCHEMY_TRACK_MODIFICATIONS=False)
    db.init_app(app)
    with app.app_context():
        db.create_all()
        clinic_a = Tenant(nome="Clínica A", slug="clinic-a")
        clinic_b = Tenant(nome="Clínica B", slug="clinic-b")
        db.session.add_all([clinic_a, clinic_b])
        db.session.flush()
        patient_a = Paciente(nome="Paciente A", tenant_id=clinic_a.id)
        patient_b = Paciente(nome="Paciente B", tenant_id=clinic_b.id)
        db.session.add_all([patient_a, patient_b])
        db.session.commit()
        patient_b_id = patient_b.id

        with app.test_request_context():
            g.active_tenant_id = clinic_a.id
            assert [p.nome for p in Paciente.query.all()] == ["Paciente A"]
            db.session.add(Atendimento(paciente_id=patient_b_id))
            with pytest.raises(PermissionError):
                db.session.commit()
            db.session.rollback()

        db.drop_all()


def test_rbac_denies_unknown_endpoints_and_limits_auditor_to_reads():
    assert role_allowed("pacientes.listar_pacientes", "GET", "auditor")
    assert not role_allowed("pacientes.novo_paciente", "POST", "auditor")
    assert not role_allowed("endpoint.nao_mapeado", "GET", "recepcao")
    assert role_allowed("consultas.nova_consulta", "POST", "recepcao")
    assert role_allowed("admin_auditoria", "GET", "auditor")
    assert not role_allowed("admin_auditoria", "GET", "medico")
    assert not role_allowed("pacientes.remover_paciente", "POST", "recepcao")
    assert not role_allowed("consultas.realizar_consulta", "POST", "recepcao")
    assert role_allowed("anything", "DELETE", "admin")
