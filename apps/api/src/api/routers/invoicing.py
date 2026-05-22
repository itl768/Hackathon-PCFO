from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from api.invoicing.application.ports import InvoiceNotFound
from api.invoicing.application.process_invoice import (
    FileTooLarge,
    UnsupportedFileType,
    UploadedDocument,
)
from api.invoicing.domain import (
    DomainEvent,
    Finding,
    FindingKind,
    Invoice,
    InvoiceStatus,
)
from api.invoicing.infrastructure.documents.local_document_store import DocumentNotFound

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


class LineItemResponse(BaseModel):
    name: str
    quantity: float
    unit_price: float
    total: float


class ExtractionResponse(BaseModel):
    invoice_number: str | None = None
    vendor_name: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    line_items: list[LineItemResponse] = Field(default_factory=list)
    total_amount: float | None = None
    tax_amount: float | None = None
    currency: str = "USD"


class FindingResponse(BaseModel):
    field_path: str
    message: str
    severity: str
    source_agent: str


class ReviewSummaryResponse(BaseModel):
    verdict: str
    text: str
    anomaly_count: int
    validation_error_count: int


class InvoiceResponse(BaseModel):
    invoice_id: UUID
    status: str
    original_filename: str
    mime_type: str
    document_url: str
    extraction: ExtractionResponse | None
    summary: ReviewSummaryResponse | None
    agent_outputs: dict[str, Any] = Field(default_factory=dict, serialization_alias="agentOutputs")
    anomalies: list[FindingResponse] = Field(default_factory=list)
    validation_errors: list[FindingResponse] = Field(default_factory=list)
    duplicate_of: UUID | None = None
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class InvoiceListItem(BaseModel):
    invoice_id: UUID
    status: str
    original_filename: str
    vendor_name: str | None
    invoice_number: str | None
    invoice_date: str | None
    total_amount: float | None
    currency: str | None
    duplicate_of: UUID | None
    created_at: datetime


class UploadResponse(BaseModel):
    invoice_id: UUID
    status: str


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UploadResponse,
    summary="Upload an invoice document",
)
async def upload_invoice(
    request: Request,
    file: UploadFile = File(...),
    force_duplicate: bool = Query(
        default=False,
        description="M0 test flag - force the deduplication node to flag this invoice as a duplicate",
    ),
) -> UploadResponse:
    content = await file.read()
    upload = UploadedDocument(
        original_filename=file.filename or "invoice",
        mime_type=file.content_type or "application/octet-stream",
        content=content,
    )

    process_invoice = request.app.state.process_invoice
    try:
        invoice = await process_invoice.execute(
            upload=upload,
            force_duplicate=force_duplicate,
        )
    except UnsupportedFileType as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {exc.mime_type}",
        ) from exc
    except FileTooLarge as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc

    return UploadResponse(invoice_id=invoice.id, status=invoice.status.value)


@router.get("", response_model=list[InvoiceListItem], summary="List recent invoices")
async def list_invoices(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[InvoiceListItem]:
    get_invoice = request.app.state.get_invoice
    invoices = await get_invoice.list_recent(limit=limit, offset=offset)
    return [_to_list_item(invoice) for invoice in invoices]


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    response_model_by_alias=True,
    summary="Get full invoice review state",
)
async def get_invoice_endpoint(invoice_id: UUID, request: Request) -> InvoiceResponse:
    get_invoice = request.app.state.get_invoice
    try:
        invoice = await get_invoice.execute(invoice_id)
    except InvoiceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_invoice_response(invoice, request)


@router.get("/{invoice_id}/document", summary="Stream the original uploaded document")
async def get_invoice_document(invoice_id: UUID, request: Request) -> Response:
    get_invoice = request.app.state.get_invoice
    document_store = request.app.state.document_store
    try:
        invoice = await get_invoice.execute(invoice_id)
    except InvoiceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        stream = document_store.stream(invoice.document_uri)
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return StreamingResponse(
        stream,
        media_type=invoice.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{invoice.original_filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@router.get("/{invoice_id}/events", summary="SSE stream of pipeline stage events")
async def stream_invoice_events(invoice_id: UUID, request: Request) -> Response:
    event_publisher = request.app.state.event_publisher

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            async for event in event_publisher.subscribe(invoice_id):
                yield {
                    "event": _event_topic(event),
                    "data": json.dumps(_event_payload(event)),
                }
            yield {
                "event": "stream_closed",
                "data": json.dumps({"invoice_id": str(invoice_id)}),
            }
        except Exception:
            logger.exception("SSE stream error for invoice %s", invoice_id)
            yield {
                "event": "error",
                "data": json.dumps({"invoice_id": str(invoice_id)}),
            }

    return EventSourceResponse(event_generator())


def _event_topic(event: DomainEvent) -> str:
    return _camel_to_snake(event.event_type)


def _camel_to_snake(name: str) -> str:
    chars: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            chars.append("_")
        chars.append(ch.lower())
    return "".join(chars)


def _event_payload(event: DomainEvent) -> dict[str, Any]:
    raw = asdict(event)
    return _jsonify(raw)


def _jsonify(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _jsonify(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonify(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonify(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _to_invoice_response(invoice: Invoice, request: Request) -> InvoiceResponse:
    extraction = _to_extraction_response(invoice)
    summary = _to_summary_response(invoice)
    anomalies = [
        _to_finding_response(f) for f in invoice.findings if f.kind is FindingKind.anomaly
    ]
    validation_errors = [
        _to_finding_response(f) for f in invoice.findings if f.kind is FindingKind.validation_error
    ]
    document_url = str(request.url_for("get_invoice_document", invoice_id=invoice.id))
    return InvoiceResponse(
        invoice_id=invoice.id,
        status=invoice.status.value,
        original_filename=invoice.original_filename,
        mime_type=invoice.mime_type,
        document_url=document_url,
        extraction=extraction,
        summary=summary,
        agent_outputs=invoice.agent_outputs,
        anomalies=anomalies,
        validation_errors=validation_errors,
        duplicate_of=invoice.duplicate_of,
        failure_reason=invoice.failure_reason,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


def _to_extraction_response(invoice: Invoice) -> ExtractionResponse | None:
    if invoice.extraction is None:
        return None
    extraction = invoice.extraction
    return ExtractionResponse(
        invoice_number=extraction.invoice_number,
        vendor_name=extraction.vendor_name,
        invoice_date=extraction.invoice_date.isoformat() if extraction.invoice_date else None,
        due_date=extraction.due_date.isoformat() if extraction.due_date else None,
        line_items=[
            LineItemResponse(
                name=item.name,
                quantity=float(item.quantity),
                unit_price=float(item.unit_price),
                total=float(item.total),
            )
            for item in extraction.line_items
        ],
        total_amount=float(extraction.total_amount) if extraction.total_amount is not None else None,
        tax_amount=float(extraction.tax_amount) if extraction.tax_amount is not None else None,
        currency=extraction.currency,
    )


def _to_summary_response(invoice: Invoice) -> ReviewSummaryResponse | None:
    if invoice.summary is None:
        return None
    return ReviewSummaryResponse(
        verdict=invoice.summary.verdict.value,
        text=invoice.summary.text,
        anomaly_count=invoice.summary.anomaly_count,
        validation_error_count=invoice.summary.validation_error_count,
    )


def _to_finding_response(finding: Finding) -> FindingResponse:
    return FindingResponse(
        field_path=finding.field_path,
        message=finding.message,
        severity=finding.severity.value,
        source_agent=finding.source_agent,
    )


def _to_list_item(invoice: Invoice) -> InvoiceListItem:
    extraction = invoice.extraction
    return InvoiceListItem(
        invoice_id=invoice.id,
        status=invoice.status.value,
        original_filename=invoice.original_filename,
        vendor_name=extraction.vendor_name if extraction else None,
        invoice_number=extraction.invoice_number if extraction else None,
        invoice_date=(
            extraction.invoice_date.isoformat()
            if extraction and extraction.invoice_date is not None
            else None
        ),
        total_amount=(
            float(extraction.total_amount)
            if extraction and extraction.total_amount is not None
            else None
        ),
        currency=extraction.currency if extraction else None,
        duplicate_of=invoice.duplicate_of,
        created_at=invoice.created_at,
    )


__all__ = ["router", "InvoiceStatus"]
