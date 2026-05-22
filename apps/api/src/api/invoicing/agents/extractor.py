from __future__ import annotations

import time
from typing import Any

from api.invoicing.agents.state import InvoiceReviewState
from api.invoicing.application.ports import (
    EventPublisher,
    ExtractionService,
    InvoiceRepository,
)
from api.invoicing.domain import (
    ExtractionFailed,
    StageCompleted,
    StageFailed,
    StageStarted,
)

STAGE_NAME = "extractor"


class ExtractorNode:
    def __init__(
        self,
        *,
        invoice_repository: InvoiceRepository,
        event_publisher: EventPublisher,
        extraction_service: ExtractionService,
        model_name: str,
    ) -> None:
        self._invoice_repository = invoice_repository
        self._event_publisher = event_publisher
        self._extraction_service = extraction_service
        self._model_name = model_name

    async def __call__(self, state: InvoiceReviewState) -> dict[str, Any]:
        invoice_id = state["invoice_id"]
        document_uri = state["document_uri"]
        mime_type = state["mime_type"]
        original_filename = state["original_filename"]

        invoice = await self._invoice_repository.get(invoice_id)
        invoice.begin_processing()
        await self._invoice_repository.save(invoice)

        await self._event_publisher.publish(
            StageStarted(invoice_id=invoice_id, stage=STAGE_NAME)
        )

        started = time.monotonic()
        try:
            extraction = await self._extraction_service.extract(
                document_uri=document_uri,
                mime_type=mime_type,
                original_filename=original_filename,
            )
        except ExtractionFailed as failure:
            latency_ms = int((time.monotonic() - started) * 1000)
            return await self._handle_failure(
                invoice_id=invoice_id,
                reason=failure.reason,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = int((time.monotonic() - started) * 1000)
            return await self._handle_failure(
                invoice_id=invoice_id,
                reason=f"Unexpected extractor error: {exc}",
                latency_ms=latency_ms,
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        agent_output: dict[str, Any] = {
            "model": self._model_name,
            "latency_ms": latency_ms,
            "field_count": extraction.filled_field_count(),
            "line_item_count": len(extraction.line_items),
            "currency": extraction.currency,
        }

        invoice = await self._invoice_repository.get(invoice_id)
        invoice.record_extraction(extraction)
        invoice.record_agent_output(STAGE_NAME, agent_output)
        await self._invoice_repository.save(invoice)

        await self._event_publisher.publish(
            StageCompleted(invoice_id=invoice_id, stage=STAGE_NAME, output=agent_output)
        )

        return {
            "extraction": extraction,
            "agent_outputs": {STAGE_NAME: agent_output},
        }

    async def _handle_failure(
        self,
        *,
        invoice_id: Any,
        reason: str,
        latency_ms: int,
    ) -> dict[str, Any]:
        agent_output: dict[str, Any] = {
            "model": self._model_name,
            "latency_ms": latency_ms,
            "error": reason,
        }

        invoice = await self._invoice_repository.get(invoice_id)
        invoice.record_agent_output(STAGE_NAME, agent_output)
        invoice.fail(reason)
        await self._invoice_repository.save(invoice)

        await self._event_publisher.publish(
            StageFailed(invoice_id=invoice_id, stage=STAGE_NAME, error=reason)
        )
        raise ExtractionFailed(reason)
