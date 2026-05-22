from __future__ import annotations

from datetime import date, timedelta

ALLOWED_FUTURE_DAYS = 30
ALLOWED_PAST_DAYS = 365


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


def is_date_in_range(invoice_date: date | None, reference: date | None = None) -> tuple[bool, str]:
    if invoice_date is None:
        return True, "Invoice date not set — skipped"

    ref = reference or today()
    future_limit = ref + timedelta(days=ALLOWED_FUTURE_DAYS)
    past_limit = ref - timedelta(days=ALLOWED_PAST_DAYS)

    if invoice_date > future_limit:
        return False, (
            f"Invoice date {invoice_date.isoformat()} is more than {ALLOWED_FUTURE_DAYS} days "
            f"after reference date {ref.isoformat()}"
        )
    if invoice_date < past_limit:
        return False, (
            f"Invoice date {invoice_date.isoformat()} is more than {ALLOWED_PAST_DAYS} days "
            f"before reference date {ref.isoformat()}"
        )
    return True, f"Invoice date {invoice_date.isoformat()} is within allowed range (ref: {ref.isoformat()})"
