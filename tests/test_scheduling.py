from datetime import datetime, timezone
import os

from flask import Flask

from core.models import Consulta, Medico, Paciente, Tenant, db
from core.scheduling import find_consultation_conflict


def make_database():
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("TEST_DATABASE_URL", "sqlite://"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    return app


def test_conflict_detection_handles_overlap_and_cancelled_records():
    app = make_database()
    with app.app_context():
        db.create_all()
        tenant = Tenant(nome="Clínica de teste", slug="teste")
        db.session.add(tenant)
        db.session.flush()
        patient = Paciente(nome="Paciente de teste", tenant_id=tenant.id)
        doctor = Medico(nome="Dra. Teste", tenant_id=tenant.id)
        db.session.add_all([patient, doctor])
        db.session.flush()

        existing = Consulta(
            paciente_id=patient.id,
            medico_id=doctor.id,
            data_hora=datetime(2026, 11, 17, 17, 0, tzinfo=timezone.utc),
            status="agendada",
            tenant_id=tenant.id,
        )
        db.session.add(existing)
        db.session.commit()

        overlapping = datetime(2026, 11, 17, 17, 30, tzinfo=timezone.utc)
        assert find_consultation_conflict(doctor.id, overlapping).id == existing.id

        adjacent = datetime(2026, 11, 17, 18, 0, tzinfo=timezone.utc)
        assert find_consultation_conflict(doctor.id, adjacent) is None

        existing.status = "cancelada"
        db.session.commit()
        assert find_consultation_conflict(doctor.id, overlapping) is None

        db.drop_all()
