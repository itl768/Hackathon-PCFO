from __future__ import annotations

from typing import Any
from uuid import UUID

from api.invoicing.agents.state import InvoiceReviewState
from api.invoicing.application.ports import EventPublisher, InvoiceRepository
from api.invoicing.domain import (
    DuplicateDetected,
    ExtractionResult,
    StageCompleted,
    StageStarted,
)

STAGE_NAME = "deduplication"


class DeduplicationNode:
    def __init__(
        self,
        *,
        invoice_repository: InvoiceRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._invoice_repository = invoice_repository
        self._event_publisher = event_publisher

    async def __call__(self, state: InvoiceReviewState) -> dict[str, Any]:
        invoice_id = state["invoice_id"]
        await self._event_publisher.publish(
            StageStarted(invoice_id=invoice_id, stage=STAGE_NAME)
        )

        force_duplicate = bool(state.get("force_duplicate", False))
        extraction = state.get("extraction")

        is_duplicate: bool
        matched_invoice_id: UUID | None
        agent_output: dict[str, Any]

        if force_duplicate:
            matched_invoice_id = invoice_id
            is_duplicate = True
            agent_output = {
                "is_duplicate": True,
                "matched_invoice_id": str(invoice_id),
                "reason": "forced_for_testing",
                "match_keys": _match_keys_from(extraction),
            }
        elif extraction is None or not extraction.has_natural_key():
            matched_invoice_id = None
            is_duplicate = False
            agent_output = {
                "is_duplicate": False,
                "matched_invoice_id": None,
                "reason": "insufficient_fields",
                "match_keys": _match_keys_from(extraction),
            }
        else:
            match = await self._invoice_repository.find_by_natural_key(
                vendor_name=extraction.vendor_name or "",
                invoice_number=extraction.invoice_number or "",
                invoice_date=extraction.invoice_date,  # type: ignore[arg-type]
                exclude_invoice_id=invoice_id,
            )
            if match is not None:
                matched_invoice_id = match.id
                is_duplicate = True
                agent_output = {
                    "is_duplicate": True,
                    "matched_invoice_id": str(match.id),
                    "reason": "natural_key_match",
                    "match_keys": _match_keys_from(extraction),
                }
            else:
                matched_invoice_id = None
                is_duplicate = False
                agent_output = {
                    "is_duplicate": False,
                    "matched_invoice_id": None,
                    "reason": "no_match",
                    "match_keys": _match_keys_from(extraction),
                }

        invoice = await self._invoice_repository.get(invoice_id)
        invoice.record_agent_output(STAGE_NAME, agent_output)
        await self._invoice_repository.save(invoice)

        if is_duplicate and matched_invoice_id is not None:
            await self._event_publisher.publish(
                DuplicateDetected(
                    invoice_id=invoice_id,
                    matched_invoice_id=matched_invoice_id,
                )
            )

        await self._event_publisher.publish(
            StageCompleted(invoice_id=invoice_id, stage=STAGE_NAME, output=agent_output)
        )

        return {
            "is_duplicate": is_duplicate,
            "matched_invoice_id": matched_invoice_id,
            "agent_outputs": {STAGE_NAME: agent_output},
        }


def _match_keys_from(extraction: ExtractionResult | None) -> dict[str, Any]:
    if extraction is None:
        return {"vendor_name": None, "invoice_number": None, "invoice_date": None}
    return {
        "vendor_name": extraction.vendor_name,
        "invoice_number": extraction.invoice_number,
        "invoice_date": (
            extraction.invoice_date.isoformat() if extraction.invoice_date else None
        ),
    }


def route_after_deduplication(state: InvoiceReviewState) -> list[str]:
    if state.get("is_duplicate"):
        return ["duplicate_handler"]
    return ["anomaly_detector", "validator"]
