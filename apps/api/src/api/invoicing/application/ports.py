from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from api.invoicing.domain import (
    DomainEvent,
    ExtractionResult,
    Finding,
    Invoice,
    InvoiceId,
    Verdict,
)


@dataclass(frozen=True)
class StoredDocument:
    document_uri: str
    sha256: str
    byte_size: int


class DocumentStore(Protocol):
    async def store(
        self,
        *,
        original_filename: str,
        mime_type: str,
        content: bytes,
    ) -> StoredDocument: ...

    async def read(self, document_uri: str) -> bytes: ...

    async def stream(self, document_uri: str) -> AsyncIterator[bytes]: ...


class InvoiceRepository(Protocol):
    async def save(self, invoice: Invoice) -> None: ...

    async def get(self, invoice_id: InvoiceId) -> Invoice: ...

    async def list_recent(self, *, limit: int = 50, offset: int = 0) -> list[Invoice]: ...

    async def find_by_natural_key(
        self,
        *,
        vendor_name: str,
        invoice_number: str,
        invoice_date: date,
        exclude_invoice_id: InvoiceId | None = None,
    ) -> Invoice | None: ...


class ExtractionService(Protocol):
    async def extract(
        self,
        *,
        document_uri: str,
        mime_type: str,
        original_filename: str,
    ) -> ExtractionResult: ...


class ReviewSummaryService(Protocol):
    async def summarize(
        self,
        *,
        extraction: ExtractionResult,
        anomalies: list[Finding],
        validation_errors: list[Finding],
        verdict: Verdict,
    ) -> str: ...


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...

    def subscribe(self, invoice_id: InvoiceId) -> AsyncIterator[DomainEvent]: ...


class PipelineRunner(Protocol):
    async def run(self, *, invoice_id: InvoiceId, force_duplicate: bool = False) -> None: ...


class InvoiceNotFound(Exception):
    def __init__(self, invoice_id: InvoiceId) -> None:
        super().__init__(f"Invoice {invoice_id} not found")
        self.invoice_id = invoice_id
