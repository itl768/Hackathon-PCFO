from __future__ import annotations

import time
from typing import Any

from api.invoicing.agents.state import InvoiceReviewState
from api.invoicing.application.ports import EventPublisher, InvoiceRepository, ReviewSummaryService
from api.invoicing.domain import (
    ReviewCompleted,
    ReviewSummary,
    StageCompleted,
    StageStarted,
    Verdict,
)

STAGE_NAME = "responder"


class ResponderNode:
    def __init__(
        self,
        *,
        invoice_repository: InvoiceRepository,
        event_publisher: EventPublisher,
        review_summary_service: ReviewSummaryService,
        model_name: str,
    ) -> None:
        self._invoice_repository = invoice_repository
        self._event_publisher = event_publisher
        self._review_summary_service = review_summary_service
        self._model_name = model_name

    async def __call__(self, state: InvoiceReviewState) -> dict[str, Any]:
        invoice_id = state["invoice_id"]
        await self._event_publisher.publish(
            StageStarted(invoice_id=invoice_id, stage=STAGE_NAME)
        )

        anomalies = list(state.get("anomalies", []))
        validation_errors = list(state.get("validation_errors", []))
        extraction = state.get("extraction")

        verdict = (
            Verdict.needs_review
            if (anomalies or validation_errors)
            else Verdict.good
        )

        summary_text = ""
        started = time.monotonic()
        if extraction is not None:
            summary_text = await self._review_summary_service.summarize(
                extraction=extraction,
                anomalies=anomalies,
                validation_errors=validation_errors,
                verdict=verdict,
            )
        else:
            summary_text = (
                "Review could not produce a summary because extraction data is missing."
            )

        latency_ms = int((time.monotonic() - started) * 1000)

        summary = ReviewSummary(
            verdict=verdict,
            text=summary_text,
            anomaly_count=len(anomalies),
            validation_error_count=len(validation_errors),
        )

        agent_output: dict[str, Any] = {
            "model": self._model_name,
            "latency_ms": latency_ms,
            "verdict": verdict.value,
            "anomaly_count": summary.anomaly_count,
            "validation_error_count": summary.validation_error_count,
        }

        invoice = await self._invoice_repository.get(invoice_id)
        invoice.attach_findings(anomalies + validation_errors)
        invoice.record_agent_output(STAGE_NAME, agent_output)
        invoice.complete_review(summary)
        await self._invoice_repository.save(invoice)

        await self._event_publisher.publish(
            StageCompleted(invoice_id=invoice_id, stage=STAGE_NAME, output=agent_output)
        )
        await self._event_publisher.publish(
            ReviewCompleted(invoice_id=invoice_id, verdict=verdict.value)
        )

        return {
            "summary": summary,
            "agent_outputs": {STAGE_NAME: agent_output},
        }
