from datetime import datetime

from mcp_toolkit.tools import date_time
from mcp_toolkit.tools.date_time import date_utils, time_now


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 4, 21, 12, 30, 0, tzinfo=tz)


def test_time_now_uses_requested_timezone(monkeypatch):
    monkeypatch.setattr(date_time, "datetime", FixedDatetime)

    result = time_now("America/New_York")

    assert "**Zona horaria:** America/New_York" in result
    assert "2026-04-21T12:30:00" in result
    assert "**UTC:**" in result


def test_time_now_rejects_invalid_timezone():
    result = time_now("Invalid/Zone")

    assert "zona horaria no válida" in result


def test_date_utils_parse_naive_datetime_with_timezone():
    result = date_utils("parse", "2026-04-21T10:00:00", timezone_name="UTC")

    assert "**ISO:** 2026-04-21T10:00:00+00:00" in result


def test_date_utils_convert_timezone():
    result = date_utils(
        "convert_timezone",
        "2026-04-21T12:00:00+00:00",
        target_timezone="America/New_York",
    )

    assert "## Conversión de zona horaria" in result
    assert "**Destino:** 2026-04-21T08:00:00-04:00" in result


def test_date_utils_add_duration():
    result = date_utils("add", "2026-04-21", amount=2, unit="days")

    assert "**Resultado:** 2026-04-23T00:00:00+00:00" in result


def test_date_utils_diff():
    result = date_utils(
        "diff",
        "2026-04-21T10:00:00+00:00",
        other_value="2026-04-22T10:00:00+00:00",
    )

    assert "**Segundos:** 86400" in result
    assert "**Horas:** 24.00" in result


def test_date_utils_rejects_invalid_action():
    result = date_utils("unknown", "2026-04-21")

    assert "action debe ser una de" in result


def test_date_utils_requires_target_timezone():
    result = date_utils("convert_timezone", "2026-04-21T10:00:00")

    assert "target_timezone es obligatorio" in result


def test_date_utils_rejects_invalid_unit():
    result = date_utils("add", "2026-04-21", amount=1, unit="months")

    assert "unidad no soportada" in result
