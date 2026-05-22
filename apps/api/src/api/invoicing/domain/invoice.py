from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from api.invoicing.domain.extraction import ExtractionResult
    from api.invoicing.domain.finding import Finding
    from api.invoicing.domain.summary import ReviewSummary


InvoiceId = UUID


class InvoiceStatus(str, Enum):
    received = "received"
    processing = "processing"
    duplicate = "duplicate"
    reviewed = "reviewed"
    confirmed = "confirmed"
    failed = "failed"


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))


@dataclass(frozen=True)
class LineItem:
    name: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal


@dataclass
class Invoice:
    id: InvoiceId
    original_filename: str
    mime_type: str
    sha256: str
    document_uri: str
    status: InvoiceStatus = InvoiceStatus.received
    extraction: ExtractionResult | None = None
    findings: list[Finding] = field(default_factory=list)
    summary: ReviewSummary | None = None
    duplicate_of: InvoiceId | None = None
    agent_outputs: dict[str, dict] = field(default_factory=dict)
    failure_reason: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1

    @classmethod
    def newly_received(
        cls,
        *,
        original_filename: str,
        mime_type: str,
        sha256: str,
        document_uri: str,
    ) -> Invoice:
        return cls(
            id=uuid4(),
            original_filename=original_filename,
            mime_type=mime_type,
            sha256=sha256,
            document_uri=document_uri,
        )

    def begin_processing(self) -> None:
        self._transition(InvoiceStatus.processing)

    def record_extraction(self, result: ExtractionResult) -> None:
        self.extraction = result
        self._touch()

    def record_agent_output(self, agent_name: str, output: dict) -> None:
        self.agent_outputs[agent_name] = output
        self._touch()

    def attach_finding(self, finding: Finding) -> None:
        self.findings.append(finding)
        self._touch()

    def attach_findings(self, findings: list[Finding]) -> None:
        if not findings:
            self._touch()
            return
        self.findings.extend(findings)
        self._touch()

    def mark_duplicate_of(self, other: InvoiceId) -> None:
        self.duplicate_of = other
        self._transition(InvoiceStatus.duplicate)

    def complete_review(self, summary: ReviewSummary) -> None:
        self.summary = summary
        self._transition(InvoiceStatus.reviewed)

    def confirm(self) -> None:
        if self.status not in {InvoiceStatus.reviewed, InvoiceStatus.duplicate}:
            raise InvalidInvoiceTransition(
                f"Cannot confirm an invoice in status {self.status.value}"
            )
        self._transition(InvoiceStatus.confirmed)

    def fail(self, reason: str) -> None:
        self.failure_reason = reason
        self._transition(InvoiceStatus.failed)

    def _transition(self, new_status: InvoiceStatus) -> None:
        self.status = new_status
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.now(UTC)
        self.version += 1


class InvalidInvoiceTransition(Exception):
    pass
