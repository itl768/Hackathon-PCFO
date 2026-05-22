from __future__ import annotations

from typing import Any

from api.invoicing.agents.state import InvoiceReviewState
from api.invoicing.application.ports import EventPublisher, InvoiceRepository
from api.invoicing.domain import StageCompleted, StageStarted

STAGE_NAME = "duplicate_handler"


class DuplicateHandlerNode:
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
        matched_invoice_id = state.get("matched_invoice_id")

        await self._event_publisher.publish(
            StageStarted(invoice_id=invoice_id, stage=STAGE_NAME)
        )

        agent_output: dict[str, Any] = {
            "matched_invoice_id": str(matched_invoice_id) if matched_invoice_id else None,
            "action": "parked_as_duplicate",
        }

        invoice = await self._invoice_repository.get(invoice_id)
        if matched_invoice_id is not None:
            invoice.mark_duplicate_of(matched_invoice_id)
        invoice.record_agent_output(STAGE_NAME, agent_output)
        await self._invoice_repository.save(invoice)

        await self._event_publisher.publish(
            StageCompleted(invoice_id=invoice_id, stage=STAGE_NAME, output=agent_output)
        )

        return {
            "agent_outputs": {STAGE_NAME: agent_output},
        }
