from __future__ import annotations

from enum import Enum

from langgraph.graph import END, START, StateGraph

from api.invoicing.agents.anomaly_detector import AnomalyDetectorNode
from api.invoicing.agents.deduplication import DeduplicationNode, route_after_deduplication
from api.invoicing.agents.duplicate_handler import DuplicateHandlerNode
from api.invoicing.agents.extractor import ExtractorNode
from api.invoicing.agents.responder import ResponderNode
from api.invoicing.agents.state import InvoiceReviewState
from api.invoicing.agents.validator import ValidatorNode
from api.invoicing.application.ports import (
    EventPublisher,
    ExtractionService,
    InvoiceRepository,
    ReviewSummaryService,
)


class StageName(str, Enum):
    extractor = "extractor"
    deduplication = "deduplication"
    anomaly_detector = "anomaly_detector"
    validator = "validator"
    responder = "responder"
    duplicate_handler = "duplicate_handler"


def build_invoice_review_graph(
    *,
    invoice_repository: InvoiceRepository,
    event_publisher: EventPublisher,
    extraction_service: ExtractionService,
    extractor_model_name: str,
    review_summary_service: ReviewSummaryService,
    responder_model_name: str,
    review_amount_tolerance: float,
):
    builder = StateGraph(InvoiceReviewState)

    builder.add_node(
        StageName.extractor.value,
        ExtractorNode(
            invoice_repository=invoice_repository,
            event_publisher=event_publisher,
            extraction_service=extraction_service,
            model_name=extractor_model_name,
        ),
    )
    builder.add_node(
        StageName.deduplication.value,
        DeduplicationNode(
            invoice_repository=invoice_repository,
            event_publisher=event_publisher,
        ),
    )
    builder.add_node(
        StageName.anomaly_detector.value,
        AnomalyDetectorNode(
            event_publisher=event_publisher,
            amount_tolerance=review_amount_tolerance,
        ),
    )
    builder.add_node(
        StageName.validator.value,
        ValidatorNode(event_publisher=event_publisher),
    )
    builder.add_node(
        StageName.responder.value,
        ResponderNode(
            invoice_repository=invoice_repository,
            event_publisher=event_publisher,
            review_summary_service=review_summary_service,
            model_name=responder_model_name,
        ),
    )
    builder.add_node(
        StageName.duplicate_handler.value,
        DuplicateHandlerNode(
            invoice_repository=invoice_repository,
            event_publisher=event_publisher,
        ),
    )

    builder.add_edge(START, StageName.extractor.value)
    builder.add_edge(StageName.extractor.value, StageName.deduplication.value)
    builder.add_conditional_edges(
        StageName.deduplication.value,
        route_after_deduplication,
        [
            StageName.duplicate_handler.value,
            StageName.anomaly_detector.value,
            StageName.validator.value,
        ],
    )
    builder.add_edge(StageName.anomaly_detector.value, StageName.responder.value)
    builder.add_edge(StageName.validator.value, StageName.responder.value)
    builder.add_edge(StageName.responder.value, END)
    builder.add_edge(StageName.duplicate_handler.value, END)

    return builder.compile()
