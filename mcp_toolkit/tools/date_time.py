"""
Herramientas de fecha/hora: hora actual, conversiones y cálculos de duración.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SUPPORTED_ACTIONS = {"parse", "convert_timezone", "add", "diff"}
SUPPORTED_UNITS = {
    "weeks": "weeks",
    "week": "weeks",
    "days": "days",
    "day": "days",
    "hours": "hours",
    "hour": "hours",
    "minutes": "minutes",
    "minute": "minutes",
    "seconds": "seconds",
    "second": "seconds",
}


def _zone(name: str) -> ZoneInfo:
    name = (name or "UTC").strip()
    if name.upper() == "UTC":
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"zona horaria no válida: {name}") from exc


def _parse_datetime(value: str, zone_name: str = "UTC") -> datetime:
    value = value.strip()
    if not value:
        raise ValueError("value no puede estar vacío")

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed_date = date.fromisoformat(value)
        parsed = datetime.combine(parsed_date, datetime.min.time())

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_zone(zone_name))
    return parsed


def _format_datetime(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _delta(amount: int, unit: str) -> timedelta:
    normalized_unit = SUPPORTED_UNITS.get(unit.lower().strip())
    if normalized_unit is None:
        raise ValueError(
            "unidad no soportada. Usa weeks, days, hours, minutes o seconds."
        )
    return timedelta(**{normalized_unit: amount})


def time_now(timezone_name: str = "UTC") -> str:
    """
    Devuelve la fecha y hora actual en una zona horaria IANA.

    Args:
        timezone_name: Zona horaria IANA, por ejemplo "UTC" o "America/New_York".

    Returns:
        Fecha y hora actual en formato ISO 8601.
    """
    try:
        tz = _zone(timezone_name)
    except ValueError as exc:
        return f"Error: {exc}"

    now = datetime.now(tz)
    return "\n".join(
        [
            "## Hora actual",
            "",
            f"**Zona horaria:** {tz.key}",
            f"**ISO:** {_format_datetime(now)}",
            f"**UTC:** {_format_datetime(now.astimezone(timezone.utc))}",
        ]
    )


def date_utils(
    action: str,
    value: str,
    timezone_name: str = "UTC",
    target_timezone: str = "",
    other_value: str = "",
    amount: int = 0,
    unit: str = "days",
) -> str:
    """
    Utilidades de fecha/hora.

    Args:
        action:          Acción: parse, convert_timezone, add o diff.
        value:           Fecha/hora ISO 8601 base.
        timezone_name:   Zona horaria para valores sin offset.
        target_timezone: Zona destino para convert_timezone.
        other_value:     Segunda fecha/hora para diff.
        amount:          Cantidad para add.
        unit:            Unidad para add: weeks, days, hours, minutes o seconds.

    Returns:
        Resultado formateado en Markdown.
    """
    action = action.lower().strip()
    if action not in SUPPORTED_ACTIONS:
        return f"Error: action debe ser una de: {', '.join(sorted(SUPPORTED_ACTIONS))}."

    try:
        base = _parse_datetime(value, timezone_name)

        if action == "parse":
            return "\n".join(
                [
                    "## Fecha parseada",
                    "",
                    f"**Input:** {value}",
                    f"**ISO:** {_format_datetime(base)}",
                    f"**UTC:** {_format_datetime(base.astimezone(timezone.utc))}",
                ]
            )

        if action == "convert_timezone":
            if not target_timezone.strip():
                return "Error: target_timezone es obligatorio para convert_timezone."
            converted = base.astimezone(_zone(target_timezone))
            return "\n".join(
                [
                    "## Conversión de zona horaria",
                    "",
                    f"**Origen:** {_format_datetime(base)}",
                    f"**Destino:** {_format_datetime(converted)}",
                    f"**Zona destino:** {converted.tzinfo.key if isinstance(converted.tzinfo, ZoneInfo) else target_timezone}",
                ]
            )

        if action == "add":
            result = base + _delta(amount, unit)
            return "\n".join(
                [
                    "## Fecha calculada",
                    "",
                    f"**Base:** {_format_datetime(base)}",
                    f"**Operación:** {amount} {unit}",
                    f"**Resultado:** {_format_datetime(result)}",
                ]
            )

        if not other_value.strip():
            return "Error: other_value es obligatorio para diff."
        other = _parse_datetime(other_value, timezone_name)
        seconds = (other - base).total_seconds()
        return "\n".join(
            [
                "## Diferencia entre fechas",
                "",
                f"**Inicio:** {_format_datetime(base)}",
                f"**Fin:** {_format_datetime(other)}",
                f"**Segundos:** {seconds:.0f}",
                f"**Minutos:** {seconds / 60:.2f}",
                f"**Horas:** {seconds / 3600:.2f}",
                f"**Días:** {seconds / 86400:.4f}",
            ]
        )
    except ValueError as exc:
        return f"Error: {exc}"
