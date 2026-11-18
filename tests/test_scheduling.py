from datetime import datetime, timezone

from flask import Flask

from core.models import Consulta, Medico, Paciente, db
from core.scheduling import find_consultation_conflict


def make_database():
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    return app


def test_conflict_detection_handles_overlap_and_cancelled_records():
    app = make_database()
    with app.app_context():
        db.create_all()
        patient = Paciente(nome="Paciente de teste")
        doctor = Medico(nome="Dra. Teste")
        db.session.add_all([patient, doctor])
        db.session.flush()

        existing = Consulta(
            paciente_id=patient.id,
            medico_id=doctor.id,
            data_hora=datetime(2026, 11, 17, 17, 0, tzinfo=timezone.utc),
            status="agendada",
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
