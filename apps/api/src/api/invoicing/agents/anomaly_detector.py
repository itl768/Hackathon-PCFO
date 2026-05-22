from __future__ import annotations

from typing import Any

from api.invoicing.agents.finding_output import findings_to_output
from api.invoicing.agents.state import InvoiceReviewState
from api.invoicing.application.ports import EventPublisher
from api.invoicing.domain import StageCompleted, StageStarted
from api.invoicing.domain.review import detect_anomalies

STAGE_NAME = "anomaly_detector"

CHECKED_RULES = [
    "invoice_date_in_future",
    "due_date_in_past",
    "no_line_items",
    "line_items_total_mismatch",
]


class AnomalyDetectorNode:
    def __init__(
        self,
        *,
        event_publisher: EventPublisher,
        amount_tolerance: float,
    ) -> None:
        self._event_publisher = event_publisher
        self._amount_tolerance = amount_tolerance

    async def __call__(self, state: InvoiceReviewState) -> dict[str, Any]:
        invoice_id = state["invoice_id"]
        await self._event_publisher.publish(
            StageStarted(invoice_id=invoice_id, stage=STAGE_NAME)
        )

        extraction = state.get("extraction")
        anomalies = detect_anomalies(
            extraction,
            tolerance=self._amount_tolerance,
        )

        agent_output: dict[str, Any] = {
            "checked": CHECKED_RULES,
            "anomaly_count": len(anomalies),
            "findings": findings_to_output(anomalies),
        }

        await self._event_publisher.publish(
            StageCompleted(invoice_id=invoice_id, stage=STAGE_NAME, output=agent_output)
        )

        return {
            "anomalies": anomalies,
            "agent_outputs": {STAGE_NAME: agent_output},
        }
