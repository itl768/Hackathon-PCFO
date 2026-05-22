from __future__ import annotations

from datetime import date, timedelta

ALLOWED_FUTURE_DAYS = 30


def today() -> date:
    return date.today()


def today_iso() -> str:
    return today().isoformat()


def parse_date(value: str | None) -> date | None:
    if not value or not str(value).strip():
        return None
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def is_after_reference(value: date | None, reference: date | None = None) -> bool:
    if value is None:
        return False
    ref = reference or today()
    return value > ref


def is_before_reference(value: date | None, reference: date | None = None) -> bool:
    if value is None:
        return False
    ref = reference or today()
    return value < ref
