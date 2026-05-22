from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict
from uuid import UUID

from api.invoicing.domain import ExtractionResult, Finding, ReviewSummary


def merge_agent_outputs(
    existing: dict[str, Any] | None,
    new: dict[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(existing or {})
    if new:
        merged.update(new)
    return merged


class InvoiceReviewState(TypedDict, total=False):
    invoice_id: UUID
    document_uri: str
    mime_type: str
    original_filename: str

    extraction: ExtractionResult | None

    is_duplicate: bool
    matched_invoice_id: UUID | None

    anomalies: Annotated[list[Finding], operator.add]
    validation_errors: Annotated[list[Finding], operator.add]

    summary: ReviewSummary | None

    agent_outputs: Annotated[dict[str, Any], merge_agent_outputs]

    force_duplicate: bool


def initial_state(
    *,
    invoice_id: UUID,
    document_uri: str,
    mime_type: str,
    original_filename: str,
    force_duplicate: bool,
) -> InvoiceReviewState:
    return InvoiceReviewState(
        invoice_id=invoice_id,
        document_uri=document_uri,
        mime_type=mime_type,
        original_filename=original_filename,
        extraction=None,
        is_duplicate=False,
        matched_invoice_id=None,
        anomalies=[],
        validation_errors=[],
        summary=None,
        agent_outputs={},
        force_duplicate=force_duplicate,
    )
