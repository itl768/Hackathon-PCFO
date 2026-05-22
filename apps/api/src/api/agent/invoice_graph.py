from __future__ import annotations

import logging
import operator
from datetime import datetime
from typing import Annotated

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from api.agent.dedup_mcp import check_exact_duplicate, store_in_history
from api.agent.deduplication import check_file_hash_duplicate, embed_text, store_embedding
from api.agent.invoice_models import (
    AnomalyResult,
    DuplicationResult,
    ExtractedInvoice,
    ValidationResult,
)
from api.agent.responder import generate_report
from api.config import settings

logger = logging.getLogger(__name__)


class InvoiceState(TypedDict):
    raw_text: str
    file_name: str
    content_hash: str
    default_currency: str
    dedup_file_result: dict | None
    extracted_invoice: dict | None
    dedup_exact_result: dict | None
    validation_result: dict | None
    anomaly_result: dict | None
    embedding_stored: bool
    report: dict | None
    skipped_steps: Annotated[list[str], operator.add]
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
    async def dedup_file_node(state: InvoiceState) -> dict:
        result = await check_file_hash_duplicate(pool, state.get("content_hash", ""))
        if result.is_duplicate:
            msg = (
                f"Duplicate file (hash match, invoice: "
                f"{result.matched_invoice_number or 'N/A'})"
            )
        else:
            msg = "No duplicate file hash in history"
        out: dict = {
            "dedup_file_result": result.model_dump(),
            "current_step": "dedup_file",
            "agent_log": [_log("DeDup File", msg, "warning" if result.is_duplicate else "success")],
        }
        if result.is_duplicate:
            out["skipped_steps"] = [
                "extract",
                "dedup_exact",
                "validate",
                "anomaly_detect",
                "embed",
            ]
        return out

    def after_dedup_file(state: InvoiceState) -> str:
        result = state.get("dedup_file_result") or {}
        return "respond" if result.get("is_duplicate") else "extract"

    async def extract_node(state: InvoiceState) -> dict:
        from api.agent.extractor import extract_invoice

        invoice = await extract_invoice(
            state["raw_text"],
            default_currency=state.get("default_currency") or settings.invoice_default_currency,
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
        result = await check_exact_duplicate(
            pool,
            invoice,
            file_name=state.get("file_name", ""),
            content_hash=state.get("content_hash", ""),
        )
        if result.is_duplicate:
            method = result.method
            msg = (
                f"Duplicate ({method}): matched invoice "
                f"{result.matched_invoice_number or 'N/A'}"
            )
        else:
            msg = "No matching invoice in history (number, date, amount, filename)"
        out: dict = {
            "dedup_exact_result": result.model_dump(),
            "current_step": "dedup_exact",
            "agent_log": [_log("DeDup MCP", msg, "warning" if result.is_duplicate else "success")],
        }
        if result.is_duplicate:
            out["skipped_steps"] = ["validate", "anomaly_detect", "embed"]
        return out

    def after_dedup_exact(state: InvoiceState) -> str:
        result = state.get("dedup_exact_result") or {}
        return "respond" if result.get("is_duplicate") else "validate"

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

    async def embed_node(state: InvoiceState) -> dict:
        extracted = ExtractedInvoice(**(state.get("extracted_invoice") or {}))
        try:
            embedding = await embed_text(state["raw_text"])
            await store_embedding(
                pool,
                state["raw_text"],
                embedding,
                {
                    "invoice_number": extracted.invoice_number,
                    "vendor_name": extracted.vendor_name,
                    "total_amount": extracted.total_amount,
                },
            )
            msg = f"Stored vector embedding ({len(embedding)} dims) for RAG search"
            status = "success"
            stored = True
        except Exception:
            logger.exception("Failed to store embedding")
            msg = "Embedding storage failed"
            status = "error"
            stored = False

        return {
            "embedding_stored": stored,
            "current_step": "embed",
            "agent_log": [_log("Embeddings", msg, status)],
        }

    async def respond_node(state: InvoiceState) -> dict:
        extracted = ExtractedInvoice(**(state.get("extracted_invoice") or {}))
        dedup_f = DuplicationResult(**(state.get("dedup_file_result") or {}))
        dedup_e = DuplicationResult(**(state.get("dedup_exact_result") or {}))
        validation = ValidationResult(**(state.get("validation_result") or {}))
        anomalies = AnomalyResult(**(state.get("anomaly_result") or {}))

        report = generate_report(extracted, dedup_f, dedup_e, validation, anomalies)

        is_duplicate = dedup_f.is_duplicate or dedup_e.is_duplicate
        try:
            if not is_duplicate and state.get("extracted_invoice"):
                await store_in_history(
                    pool,
                    extracted,
                    report.decision,
                    report.risk_score,
                    report.model_dump(),
                    file_hash=state.get("content_hash", ""),
                    file_name=state.get("file_name", ""),
                )
        except Exception:
            logger.exception("Failed to persist invoice history")

        status = "success" if "Approve" in report.decision else ("error" if "Reject" in report.decision else "warning")
        return {
            "report": report.model_dump(),
            "current_step": "respond",
            "agent_log": [
                _log("Responder", f"Decision: {report.decision} (confidence: {report.confidence})", status)
            ],
        }

    graph = StateGraph(InvoiceState)
    graph.add_node("dedup_file", dedup_file_node)
    graph.add_node("extract", extract_node)
    graph.add_node("dedup_exact", dedup_exact_node)
    graph.add_node("validate", validate_node)
    graph.add_node("anomaly_detect", anomaly_node)
    graph.add_node("embed", embed_node)
    graph.add_node("respond", respond_node)

    graph.add_edge(START, "dedup_file")
    graph.add_conditional_edges(
        "dedup_file",
        after_dedup_file,
        {"extract": "extract", "respond": "respond"},
    )
    graph.add_edge("extract", "dedup_exact")
    graph.add_conditional_edges(
        "dedup_exact",
        after_dedup_exact,
        {"validate": "validate", "respond": "respond"},
    )
    graph.add_edge("validate", "anomaly_detect")
    graph.add_edge("anomaly_detect", "embed")
    graph.add_edge("embed", "respond")
    graph.add_edge("respond", END)

    return graph.compile()
