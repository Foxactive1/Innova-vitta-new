import pytest
from datetime import date, datetime, timezone

from core.time_utils import local_day_utc_bounds, local_to_utc, utc_to_local

def test_naive_clinic_datetime_is_converted_to_utc():
    value = local_to_utc(datetime(2026, 11, 17, 14, 30))
    assert value == datetime(2026, 11, 17, 17, 30, tzinfo=timezone.utc)

def test_aware_datetime_is_converted_to_utc():
    value = local_to_utc(datetime(2026, 11, 17, 14, 30, tzinfo=timezone.utc))
    assert value == datetime(2026, 11, 17, 14, 30, tzinfo=timezone.utc)

def test_utc_value_is_rendered_in_clinic_timezone():
    value = utc_to_local(datetime(2026, 11, 17, 17, 30, tzinfo=timezone.utc))
    assert (value.hour, value.minute) == (14, 30)

def test_local_day_bounds_cover_the_local_day():
    start, end = local_day_utc_bounds(date(2026, 11, 17))
    assert start == datetime(2026, 11, 17, 3, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 11, 18, 3, 0, tzinfo=timezone.utc)

def test_invalid_datetime_input_returns_none():
    from core.utils import parse_data_hora
    assert parse_data_hora("17/11/2026", "14:30") is None

def test_valid_datetime_input_uses_clinic_timezone():
    from core.utils import parse_data_hora
    assert parse_data_hora("2026-11-17", "14:30") == datetime(2026, 11, 17, 17, 30, tzinfo=timezone.utc)
