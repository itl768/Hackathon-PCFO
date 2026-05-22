from __future__ import annotations

import logging
import operator
from datetime import datetime
from typing import Annotated

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from api.agent.dedup_mcp import check_exact_duplicate, store_in_history
from api.agent.deduplication import check_vector_duplicate, embed_text, store_embedding
from api.agent.invoice_models import (
    AnomalyResult,
    DuplicationResult,
    ExtractedInvoice,
    ValidationResult,
)
from api.agent.responder import generate_report

logger = logging.getLogger(__name__)


class InvoiceState(TypedDict):
    raw_text: str
    file_name: str
    default_currency: str
    embedding: list[float]
    dedup_vector_result: dict | None
    extracted_invoice: dict | None
    dedup_exact_result: dict | None
    validation_result: dict | None
    anomaly_result: dict | None
    report: dict | None
    current_step: str
    agent_log: Annotated[list[dict], operator.add]


def _log(agent: str, message: str, status: str = "info") -> dict:
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent_name": agent,
        "message": message,
        "status": status,
    }


def build_invoice_graph(pool):
    async def dedup_vector_node(state: InvoiceState) -> dict:
        embedding = await embed_text(state["raw_text"])
        result = await check_vector_duplicate(pool, embedding)
        msg = (
            f"Duplicate found (similarity: {result.similarity_score:.2f}, "
            f"matched: {result.matched_invoice_number or 'N/A'})"
            if result.is_duplicate
            else f"No duplicates found (max similarity: {result.similarity_score:.2f})"
        )
        return {
            "embedding": embedding,
            "dedup_vector_result": result.model_dump(),
            "current_step": "dedup_vector",
            "agent_log": [_log("DeDup Vector", msg, "warning" if result.is_duplicate else "success")],
        }

    def after_dedup_vector(state: InvoiceState) -> str:
        result = state.get("dedup_vector_result") or {}
        return "respond" if result.get("is_duplicate") else "extract"

    async def extract_node(state: InvoiceState) -> dict:
        from api.agent.extractor import extract_invoice

        invoice = await extract_invoice(
            state["raw_text"],
            default_currency=state.get("default_currency"),
        )
        n = len(invoice.line_items)
        return {
            "extracted_invoice": invoice.model_dump(),
            "current_step": "extract",
            "agent_log": [
                _log(
                    "Extractor",
                    f"Extracted {n} line items, total: {invoice.currency} {invoice.total_amount or 0:,.2f}",
                    "success",
                )
            ],
        }

    async def dedup_exact_node(state: InvoiceState) -> dict:
        invoice = ExtractedInvoice(**(state["extracted_invoice"] or {}))
        result = await check_exact_duplicate(pool, invoice)
        if result.is_duplicate:
            msg = f"Exact match found (invoice: {result.matched_invoice_number})"
        else:
            msg = "No exact match in history"
        return {
            "dedup_exact_result": result.model_dump(),
            "current_step": "dedup_exact",
            "agent_log": [_log("DeDup MCP", msg, "warning" if result.is_duplicate else "success")],
        }

    async def validate_node(state: InvoiceState) -> dict:
        from api.agent.validator import validate_invoice

        invoice = ExtractedInvoice(**(state["extracted_invoice"] or {}))
        result = validate_invoice(invoice)
        passed = sum(1 for r in result.rules if r.passed)
        total = len(result.rules)
        failed = [r.rule_name for r in result.rules if not r.passed]
        msg = f"{passed}/{total} rules passed"
        if failed:
            msg += f", failed: {', '.join(failed)}"
        return {
            "validation_result": result.model_dump(),
            "current_step": "validate",
            "agent_log": [_log("Validator", msg, "success" if result.all_passed else "warning")],
        }

    async def anomaly_node(state: InvoiceState) -> dict:
        from api.agent.anomaly_detector import detect_anomalies

        invoice = ExtractedInvoice(**(state["extracted_invoice"] or {}))
        validation = ValidationResult(**(state["validation_result"] or {}))
        result = await detect_anomalies(invoice, validation)
        status = "success" if result.risk_score < 30 else ("warning" if result.risk_score < 70 else "error")
        return {
            "anomaly_result": result.model_dump(),
            "current_step": "anomaly_detect",
            "agent_log": [
                _log(
                    "Anomaly Detector",
                    f"Risk score: {result.risk_score}/100, {len(result.flags)} flag(s) detected",
                    status,
                )
            ],
        }

    async def respond_node(state: InvoiceState) -> dict:
        extracted = ExtractedInvoice(**(state.get("extracted_invoice") or {}))
        dedup_v = DuplicationResult(**(state.get("dedup_vector_result") or {}))
        dedup_e = DuplicationResult(**(state.get("dedup_exact_result") or {}))
        validation = ValidationResult(**(state.get("validation_result") or {}))
        anomalies = AnomalyResult(**(state.get("anomaly_result") or {}))

        report = generate_report(extracted, dedup_v, dedup_e, validation, anomalies)

        try:
            if state.get("embedding") and state.get("extracted_invoice"):
                await store_embedding(
                    pool,
                    state["raw_text"],
                    state["embedding"],
                    {
                        "invoice_number": extracted.invoice_number,
                        "vendor_name": extracted.vendor_name,
                        "total_amount": extracted.total_amount,
                    },
                )
                await store_in_history(
                    pool, extracted, report.decision, report.risk_score, report.model_dump()
                )
        except Exception:
            logger.exception("Failed to persist invoice data")

        status = "success" if "Approve" in report.decision else ("error" if "Reject" in report.decision else "warning")
        return {
            "report": report.model_dump(),
            "current_step": "respond",
            "agent_log": [
                _log("Responder", f"Decision: {report.decision} (confidence: {report.confidence})", status)
            ],
        }

    graph = StateGraph(InvoiceState)
    graph.add_node("dedup_vector", dedup_vector_node)
    graph.add_node("extract", extract_node)
    graph.add_node("dedup_exact", dedup_exact_node)
    graph.add_node("validate", validate_node)
    graph.add_node("anomaly_detect", anomaly_node)
    graph.add_node("respond", respond_node)

    graph.add_edge(START, "dedup_vector")
    graph.add_conditional_edges(
        "dedup_vector",
        after_dedup_vector,
        {"extract": "extract", "respond": "respond"},
    )
    graph.add_edge("extract", "dedup_exact")
    graph.add_edge("dedup_exact", "validate")
    graph.add_edge("validate", "anomaly_detect")
    graph.add_edge("anomaly_detect", "respond")
    graph.add_edge("respond", END)

    return graph.compile()
