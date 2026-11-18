"""Database-portable consultation overlap checks."""
from datetime import datetime, timedelta

from .models import Consulta
from .time import as_utc, local_day_bounds

DEFAULT_APPOINTMENT_MINUTES = 60


def find_consultation_conflict(medico_id: int, start: datetime,
                               duration_minutes: int = DEFAULT_APPOINTMENT_MINUTES,
                               exclude_id: int | None = None):
    """Return the conflicting consultation, or None.

    The overlap comparison is performed in Python after a bounded SQL query,
    avoiding dialect-specific datetime arithmetic (SQLite vs PostgreSQL).
    Existing appointments retain the current 60-minute default because the
    current schema does not store per-service duration.
    """
    if duration_minutes <= 0 or duration_minutes > 24 * 60:
        raise ValueError("duration_minutes must be between 1 and 1440")

    start_utc = as_utc(start)
    end_utc = start_utc + timedelta(minutes=duration_minutes)
    local_day = start_utc.astimezone(__import__("zoneinfo").ZoneInfo("America/Sao_Paulo")).date()
    day_start, day_end = local_day_bounds(local_day)
    search_start = day_start - timedelta(days=1)
    search_end = day_end + timedelta(days=1)

    query = Consulta.query.filter(
        Consulta.medico_id == medico_id,
        Consulta.status != "cancelada",
        Consulta.data_hora >= search_start,
        Consulta.data_hora < search_end,
    )
    if exclude_id is not None:
        query = query.filter(Consulta.id != exclude_id)

    for existing in query.all():
        existing_start = as_utc(existing.data_hora)
        existing_end = existing_start + timedelta(minutes=DEFAULT_APPOINTMENT_MINUTES)
        if existing_start < end_utc and existing_end > start_utc:
            return existing
    return None
