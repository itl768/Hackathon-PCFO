from __future__ import annotations

from typing import Any

from api.invoicing.agents.finding_output import findings_to_output
from api.invoicing.agents.state import InvoiceReviewState
from api.invoicing.application.ports import EventPublisher
from api.invoicing.domain import StageCompleted, StageStarted
from api.invoicing.domain.review import validate_extraction

STAGE_NAME = "validator"

CHECKED_RULES = [
    "required_fields_present",
    "field_types_correct",
    "line_items_shape_correct",
    "schema_conformance",
]


class ValidatorNode:
    def __init__(self, *, event_publisher: EventPublisher) -> None:
        self._event_publisher = event_publisher

    async def __call__(self, state: InvoiceReviewState) -> dict[str, Any]:
        invoice_id = state["invoice_id"]
        await self._event_publisher.publish(
            StageStarted(invoice_id=invoice_id, stage=STAGE_NAME)
        )

        extraction = state.get("extraction")
        validation_errors = validate_extraction(extraction)

        agent_output: dict[str, Any] = {
            "checked": CHECKED_RULES,
            "validation_error_count": len(validation_errors),
            "findings": findings_to_output(validation_errors),
        }

        await self._event_publisher.publish(
            StageCompleted(invoice_id=invoice_id, stage=STAGE_NAME, output=agent_output)
        )

        return {
            "validation_errors": validation_errors,
            "agent_outputs": {STAGE_NAME: agent_output},
        }
