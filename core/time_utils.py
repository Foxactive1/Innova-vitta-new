"""Conversoes de data/hora para a zona operacional da clinica.
Persistencia em UTC; entrada, exibicao e calendario em America/Sao_Paulo.
"""
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

CLINIC_TIMEZONE = ZoneInfo("America/Sao_Paulo")

def local_to_utc(value: datetime) -> datetime:
    """Interpreta datetime naive como horario local e converte para UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=CLINIC_TIMEZONE)
    return value.astimezone(timezone.utc)

def local_day_utc_bounds(day: date) -> tuple[datetime, datetime]:
    """Retorna intervalo semiaberto do dia local convertido para UTC."""
    start_local = datetime.combine(day, time.min, tzinfo=CLINIC_TIMEZONE)
    next_day = date.fromordinal(day.toordinal() + 1)
    end_local = datetime.combine(next_day, time.min, tzinfo=CLINIC_TIMEZONE)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

def utc_to_local(value: datetime) -> datetime:
    """Converte datetime persistido em UTC para a zona da clinica."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(CLINIC_TIMEZONE)
