"""Conversões temporais determinísticas para o modelo canônico do relatório."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

DISPLAY_TIMEZONE = timezone(timedelta(hours=-3), name="America/Sao_Paulo")
UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
REPORT_DATETIME_FORMAT = "%d/%m/%Y %H:%M"


def ensure_utc(value: datetime, *, naive_timezone=DISPLAY_TIMEZONE) -> datetime:
    """Converte datetime para UTC; valores sem fuso são horários operacionais locais."""

    if not isinstance(value, datetime):
        raise TypeError("value precisa ser datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=naive_timezone)
    return value.astimezone(UTC)


def datetime_to_unix(value: datetime, *, naive_timezone=DISPLAY_TIMEZONE) -> int:
    """Calcula Unix timestamp por aritmética, inclusive antes de 1970 no Windows."""

    delta = ensure_utc(value, naive_timezone=naive_timezone) - UNIX_EPOCH
    return int(delta.total_seconds())


def unix_to_datetime(value: int | float, *, target_timezone=UTC) -> datetime:
    """Converte Unix timestamp sem depender de ``datetime.fromtimestamp``."""

    return (UNIX_EPOCH + timedelta(seconds=float(value))).astimezone(target_timezone)


def parse_report_timestamp(value) -> int | None:
    """Aceita epoch ou data textual do relatório; zero continua significando ausência."""

    if value in (None, "", "0", 0):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.strptime(str(value), REPORT_DATETIME_FORMAT)
            return datetime_to_unix(parsed)
        except (TypeError, ValueError, OverflowError):
            return None


def format_report_timestamp(value) -> str:
    """Formata epoch no horário operacional explícito, sem usar o fuso do sistema."""

    if value is None:
        return "-"
    try:
        return unix_to_datetime(
            int(value),
            target_timezone=DISPLAY_TIMEZONE,
        ).strftime(REPORT_DATETIME_FORMAT)
    except (TypeError, ValueError, OverflowError):
        return "-"


def now_utc() -> datetime:
    return datetime.now(UTC)


def now_display() -> datetime:
    return datetime.now(DISPLAY_TIMEZONE)
