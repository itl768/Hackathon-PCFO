from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from api.invoicing.domain import DomainEvent


def event_to_payload(event: DomainEvent) -> dict[str, Any]:
    payload = asdict(event)
    return _normalize(payload)


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value
