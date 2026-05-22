from __future__ import annotations

import asyncio
import logging

from api.invoicing.agents.graph import build_invoice_review_graph
from api.invoicing.agents.state import initial_state
from api.invoicing.application.ports import (
    EventPublisher,
    ExtractionService,
    InvoiceNotFound,
    InvoiceRepository,
    ReviewSummaryService,
)
from api.invoicing.domain import InvoiceId, StageFailed
from api.invoicing.infrastructure.messaging.in_process_publisher import InProcessEventPublisher

logger = logging.getLogger(__name__)


class LangGraphPipelineRunner:
    def __init__(
        self,
        *,
        invoice_repository: InvoiceRepository,
        event_publisher: EventPublisher,
        extraction_service: ExtractionService,
        extractor_model_name: str,
        review_summary_service: ReviewSummaryService,
        responder_model_name: str,
        review_amount_tolerance: float,
    ) -> None:
        self._invoice_repository = invoice_repository
        self._event_publisher = event_publisher
        self._graph = build_invoice_review_graph(
            invoice_repository=invoice_repository,
            event_publisher=event_publisher,
            extraction_service=extraction_service,
            extractor_model_name=extractor_model_name,
            review_summary_service=review_summary_service,
            responder_model_name=responder_model_name,
            review_amount_tolerance=review_amount_tolerance,
        )
        self._background_tasks: set[asyncio.Task] = set()

    async def run(self, *, invoice_id: InvoiceId, force_duplicate: bool = False) -> None:
        task = asyncio.create_task(self._execute(invoice_id, force_duplicate))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _execute(self, invoice_id: InvoiceId, force_duplicate: bool) -> None:
        try:
            invoice = await self._invoice_repository.get(invoice_id)
        except InvoiceNotFound:
            logger.exception("Pipeline run requested for missing invoice %s", invoice_id)
            await self._close_publisher(invoice_id)
            return

        state = initial_state(
            invoice_id=invoice_id,
            document_uri=invoice.document_uri,
            mime_type=invoice.mime_type,
            original_filename=invoice.original_filename,
            force_duplicate=force_duplicate,
        )

        try:
            await self._graph.ainvoke(state)
        except Exception as exc:
            logger.exception("Pipeline failed for invoice %s", invoice_id)
            await self._record_failure(invoice_id, str(exc))
        finally:
            await self._close_publisher(invoice_id)

    async def _record_failure(self, invoice_id: InvoiceId, reason: str) -> None:
        try:
            invoice = await self._invoice_repository.get(invoice_id)
            invoice.fail(reason)
            await self._invoice_repository.save(invoice)
        except Exception:
            logger.exception("Failed to persist invoice failure for %s", invoice_id)
        await self._event_publisher.publish(
            StageFailed(invoice_id=invoice_id, stage="pipeline", error=reason)
        )

    async def _close_publisher(self, invoice_id: InvoiceId) -> None:
        if isinstance(self._event_publisher, InProcessEventPublisher):
            await self._event_publisher.close(invoice_id)
