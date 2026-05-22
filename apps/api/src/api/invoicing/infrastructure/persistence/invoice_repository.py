from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.invoicing.application.ports import InvoiceNotFound, InvoiceRepository
from api.invoicing.domain import (
    ExtractionResult,
    Finding,
    FindingKind,
    Invoice,
    InvoiceId,
    InvoiceStatus,
    LineItemDraft,
    ReviewSummary,
    Severity,
    Verdict,
)
from api.invoicing.infrastructure.persistence.models import (
    FindingRecord,
    InvoiceRecord,
    LineItemRecord,
)
from api.invoicing.infrastructure.persistence.session import SessionFactory


class SqlInvoiceRepository(InvoiceRepository):
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def save(self, invoice: Invoice) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                record = await session.get(InvoiceRecord, invoice.id)
                if record is None:
                    record = InvoiceRecord(id=invoice.id)
                    session.add(record)
                _apply_to_record(invoice, record)

    async def get(self, invoice_id: InvoiceId) -> Invoice:
        async with self._session_factory() as session:
            record = await session.get(InvoiceRecord, invoice_id)
            if record is None:
                raise InvoiceNotFound(invoice_id)
            return _to_domain(record)

    async def list_recent(self, *, limit: int = 50, offset: int = 0) -> list[Invoice]:
        async with self._session_factory() as session:
            stmt = (
                select(InvoiceRecord)
                .order_by(InvoiceRecord.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return [_to_domain(record) for record in result.scalars().all()]

    async def find_by_natural_key(
        self,
        *,
        vendor_name: str,
        invoice_number: str,
        invoice_date: date,
        exclude_invoice_id: InvoiceId | None = None,
    ) -> Invoice | None:
        async with self._session_factory() as session:
            stmt = (
                select(InvoiceRecord)
                .where(
                    InvoiceRecord.extracted_json["vendor_name"].as_string() == vendor_name,
                    InvoiceRecord.extracted_json["invoice_number"].as_string() == invoice_number,
                    InvoiceRecord.extracted_json["invoice_date"].as_string()
                    == invoice_date.isoformat(),
                    InvoiceRecord.status != InvoiceStatus.failed.value,
                )
                .order_by(InvoiceRecord.created_at.asc())
                .limit(1)
            )
            if exclude_invoice_id is not None:
                stmt = stmt.where(InvoiceRecord.id != exclude_invoice_id)
            result = await session.execute(stmt)
            record = result.scalars().first()
            if record is None:
                return None
            return _to_domain(record)


def _apply_to_record(invoice: Invoice, record: InvoiceRecord) -> None:
    record.status = invoice.status.value
    record.original_filename = invoice.original_filename
    record.mime_type = invoice.mime_type
    record.sha256 = invoice.sha256
    record.document_uri = invoice.document_uri
    record.extracted_json = (
        invoice.extraction.model_dump(mode="json") if invoice.extraction is not None else None
    )
    record.summary_text = invoice.summary.text if invoice.summary is not None else None
    record.verdict = invoice.summary.verdict.value if invoice.summary is not None else None
    record.duplicate_of = invoice.duplicate_of
    record.agent_outputs = dict(invoice.agent_outputs)
    record.failure_reason = invoice.failure_reason
    record.version = invoice.version
    record.created_at = invoice.created_at
    record.updated_at = invoice.updated_at

    record.line_items = _build_line_item_records(invoice)
    record.findings = _build_finding_records(invoice)


def _build_line_item_records(invoice: Invoice) -> list[LineItemRecord]:
    if invoice.extraction is None:
        return []
    items: list[LineItemRecord] = []
    for position, draft in enumerate(invoice.extraction.line_items):
        items.append(
            LineItemRecord(
                invoice_id=invoice.id,
                position=position,
                name=draft.name,
                quantity=Decimal(draft.quantity),
                unit_price=Decimal(draft.unit_price),
                total=Decimal(draft.total),
            )
        )
    return items


def _build_finding_records(invoice: Invoice) -> list[FindingRecord]:
    return [
        FindingRecord(
            invoice_id=invoice.id,
            kind=finding.kind.value,
            severity=finding.severity.value,
            field_path=finding.field_path,
            message=finding.message,
            source_agent=finding.source_agent,
            created_at=finding.detected_at,
        )
        for finding in invoice.findings
    ]


def _to_domain(record: InvoiceRecord) -> Invoice:
    extraction = _extraction_from_json(record.extracted_json)
    summary = _summary_from_record(record)
    findings = [_finding_from_record(item) for item in record.findings]

    return Invoice(
        id=record.id,
        original_filename=record.original_filename,
        mime_type=record.mime_type,
        sha256=record.sha256,
        document_uri=record.document_uri,
        status=InvoiceStatus(record.status),
        extraction=extraction,
        findings=findings,
        summary=summary,
        duplicate_of=record.duplicate_of,
        agent_outputs=dict(record.agent_outputs or {}),
        failure_reason=record.failure_reason,
        created_at=record.created_at,
        updated_at=record.updated_at,
        version=record.version,
    )


def _extraction_from_json(payload: dict[str, Any] | None) -> ExtractionResult | None:
    if payload is None:
        return None
    return ExtractionResult.model_validate(payload)


def _summary_from_record(record: InvoiceRecord) -> ReviewSummary | None:
    if record.summary_text is None and record.verdict is None:
        return None
    anomaly_count = sum(1 for f in record.findings if f.kind == FindingKind.anomaly.value)
    validation_error_count = sum(
        1 for f in record.findings if f.kind == FindingKind.validation_error.value
    )
    return ReviewSummary(
        verdict=Verdict(record.verdict) if record.verdict is not None else Verdict.good,
        text=record.summary_text or "",
        anomaly_count=anomaly_count,
        validation_error_count=validation_error_count,
    )


def _finding_from_record(record: FindingRecord) -> Finding:
    return Finding(
        kind=FindingKind(record.kind),
        severity=Severity(record.severity),
        field_path=record.field_path,
        message=record.message,
        source_agent=record.source_agent,
        detected_at=record.created_at,
    )


def _line_item_draft_from_record(record: LineItemRecord) -> LineItemDraft:
    return LineItemDraft(
        name=record.name,
        quantity=record.quantity,
        unit_price=record.unit_price,
        total=record.total,
    )
