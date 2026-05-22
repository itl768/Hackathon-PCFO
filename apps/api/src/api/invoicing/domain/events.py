from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from api.invoicing.domain.invoice import InvoiceId


@dataclass(frozen=True)
class DomainEvent:
    invoice_id: InvoiceId
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        return type(self).__name__


@dataclass(frozen=True)
class InvoiceReceived(DomainEvent):
    original_filename: str = ""
    mime_type: str = ""


@dataclass(frozen=True)
class StageStarted(DomainEvent):
    stage: str = ""


@dataclass(frozen=True)
class StageCompleted(DomainEvent):
    stage: str = ""
    output: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StageFailed(DomainEvent):
    stage: str = ""
    error: str = ""


@dataclass(frozen=True)
class DuplicateDetected(DomainEvent):
    matched_invoice_id: InvoiceId | None = None


@dataclass(frozen=True)
class ReviewCompleted(DomainEvent):
    verdict: str = ""
