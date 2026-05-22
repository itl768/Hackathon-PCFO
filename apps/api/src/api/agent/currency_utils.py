from __future__ import annotations

SUPPORTED_CURRENCIES: tuple[str, ...] = (
    "USD",
    "EUR",
    "GBP",
    "LKR",
    "AUD",
    "CAD",
    "CHF",
    "JPY",
    "INR",
    "SGD",
    "AED",
    "SAR",
)


def normalize_currency(code: str | None, fallback: str = "USD") -> str:
    raw = (code or "").strip().upper()
    if len(raw) >= 3:
        normalized = raw[:3]
    elif raw:
        normalized = raw
    else:
        normalized = fallback.upper()[:3]

    if normalized in SUPPORTED_CURRENCIES:
        return normalized
    return fallback.upper()[:3]
