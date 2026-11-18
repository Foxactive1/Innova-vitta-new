from datetime import date, datetime, timezone

from core.time import (
    as_clinic_time,
    as_utc,
    local_day_bounds,
    parse_local_datetime,
)


def test_local_appointment_time_is_normalized_to_utc():
    value = parse_local_datetime("2026-11-17", "14:30")
    assert value == datetime(2026, 11, 17, 17, 30, tzinfo=timezone.utc)


def test_invalid_local_datetime_returns_none():
    assert parse_local_datetime("2026-02-30", "14:30") is None
    assert parse_local_datetime("2026-11-17", "25:00") is None


def test_local_day_bounds_cover_exact_sao_paulo_calendar_day():
    start, end = local_day_bounds(date(2026, 11, 17))
    assert start == datetime(2026, 11, 17, 3, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 11, 18, 3, 0, tzinfo=timezone.utc)


def test_naive_sqlite_datetime_is_treated_as_utc():
    naive = datetime(2026, 11, 17, 17, 0)
    assert as_utc(naive) == datetime(2026, 11, 17, 17, 0, tzinfo=timezone.utc)
    assert as_clinic_time(naive).hour == 14
