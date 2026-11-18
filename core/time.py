"""Timezone helpers for clinic operations.

Naive date/time values entered by clinic staff are interpreted in
America/Sao_Paulo and normalized to UTC for persistence.
"""
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

CLINIC_TIMEZONE = ZoneInfo("America/Sao_Paulo")
UTC = timezone.utc


def local_now() -> datetime:
    return datetime.now(CLINIC_TIMEZONE)


def parse_local_datetime(date_value: str, time_value: str) -> datetime | None:
    if not date_value or not time_value:
        return None
    try:
        local_value = datetime.strptime(
            f"{date_value} {time_value}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=CLINIC_TIMEZONE)
        return local_value.astimezone(UTC)
    except (TypeError, ValueError):
        return None


def local_day_bounds(day: date) -> tuple[datetime, datetime]:
    """Return UTC-aware half-open bounds for a clinic-local calendar day."""
    start = datetime.combine(day, time.min, tzinfo=CLINIC_TIMEZONE)
    end = datetime.combine(day.fromordinal(day.toordinal() + 1), time.min,
                           tzinfo=CLINIC_TIMEZONE)
    return start.astimezone(UTC), end.astimezone(UTC)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        # SQLite commonly returns naive values for timezone=True columns.
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def as_clinic_time(value: datetime) -> datetime:
    return as_utc(value).astimezone(CLINIC_TIMEZONE)
