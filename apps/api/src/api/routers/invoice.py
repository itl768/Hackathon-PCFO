from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import AsyncGenerator

from fastapi import APIRouter, File, Form, Request, UploadFile
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from api.agent.document_reader import read_document
from api.agent.invoice_graph import build_invoice_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invoice", tags=["invoice"])

SAMPLE_INVOICES = [
    {
        "id": "clean",
        "name": "Clean Invoice (Auto-Approve)",
        "description": "All fields correct, totals match, VAT valid — should auto-approve",
        "text": """INVOICE

From: TechFlow Solutions Ltd.
123 Innovation Street, London, UK

Invoice Number: TFS-2024-001
Invoice Date: {invoice_date}
Due Date: {due_date}

Bill To:
Gapstars Engineering
42 Innovation Drive, Colombo, Sri Lanka

Items:
| Description                  | Qty | Unit Price | Net       | VAT (10%) | Total     |
|------------------------------|-----|------------|-----------|-----------|-----------|
| Cloud Infrastructure Setup   | 1   | $2,500.00  | $2,500.00 | $250.00   | $2,750.00 |
| API Development (40 hours)   | 40  | $75.00     | $3,000.00 | $300.00   | $3,300.00 |
| Security Audit               | 1   | $1,500.00  | $1,500.00 | $150.00   | $1,650.00 |

Subtotal: $7,000.00
VAT Total (10%): $700.00
Total Amount: $7,700.00

Currency: USD
Payment Terms: Net 30
Bank: HSBC UK | Account: 12345678 | Sort: 40-20-10""",
    },
    {
        "id": "anomalous",
        "name": "Anomalous Invoice (Flagged)",
        "description": "Line total mismatch, missing due date, round-number padding",
        "text": """INVOICE

Vendor: QuickBill Corp
Invoice #: QBC-9921
Invoice Date: {invoice_date}

Bill To: Gapstars Engineering

Items:
| Description                | Qty | Unit Price | Net       | VAT (10%) | Total     |
|----------------------------|-----|------------|-----------|-----------|-----------|
| Premium Consulting Package | 1   | $5,000.00  | $5,000.00 | $500.00   | $5,500.00 |
| Data Migration Service     | 1   | $3,000.00  | $3,000.00 | $300.00   | $3,300.00 |
| Support Package            | 1   | $2,000.00  | $2,000.00 | $200.00   | $2,000.00 |

Subtotal: $10,000.00
VAT: $1,000.00
TOTAL: $12,000.00

NOTE: Due date not specified. Round payment preferred.""",
    },
    {
        "id": "high_value",
        "name": "High-Value Invoice (Manual Review)",
        "description": "Large amount ($83,950), correct data but triggers threshold",
        "text": """INVOICE

From: GlobalTech Enterprises Inc.
500 Enterprise Blvd, San Francisco, CA 94105

Invoice Number: GTE-2024-5547
Date: {invoice_date}
Due Date: {due_date}

Bill To:
Gapstars Engineering
42 Innovation Drive, Colombo, Sri Lanka

| Description                    | Qty | Unit Price  | Net        | VAT (15%)  | Total      |
|--------------------------------|-----|-------------|------------|------------|------------|
| Enterprise Software License    | 10  | $5,000.00   | $50,000.00 | $7,500.00  | $57,500.00 |
| Implementation & Training      | 1   | $15,000.00  | $15,000.00 | $2,250.00  | $17,250.00 |
| Annual Maintenance Contract    | 1   | $8,000.00   | $8,000.00  | $1,200.00  | $9,200.00  |

Subtotal: $73,000.00
VAT Total (15%): $10,950.00
Grand Total: $83,950.00

Currency: USD
Payment Terms: Net 15

NOTES: Urgent processing requested. Purchase order PO-2024-889 attached.""",
    },
]


class ChatRequest(BaseModel):
    message: str
    thread_id: str = ""


def _materialize_samples() -> list[dict]:
    today = date.today()
    invoice_date = today.isoformat()
    due_date = (today + timedelta(days=30)).isoformat()
    out = []
    for s in SAMPLE_INVOICES:
        text = s["text"].format(invoice_date=invoice_date, due_date=due_date)
        out.append(
            {
                "id": s["id"],
                "name": s["name"],
                "description": s["description"],
                "text": text,
            }
        )
    return out


@router.get("/samples")
async def get_samples():
    return _materialize_samples()


@router.get("/history")
async def get_history(request: Request):
    pool = request.app.state.invoice_pool
    async with pool.connection() as conn:
        cur = await conn.execute(
            """
            SELECT id, invoice_number, vendor_name, total_amount, status,
                   risk_score, currency, invoice_date, processed_at
            FROM invoice_history
            ORDER BY processed_at DESC
            LIMIT 20
            """
        )
        rows = await cur.fetchall()

    return [
        {
            "id": r[0],
            "invoice_number": r[1],
            "vendor_name": r[2],
            "total_amount": float(r[3]) if r[3] else None,
            "status": r[4],
            "risk_score": r[5],
            "currency": r[6],
            "invoice_date": r[7],
            "processed_at": str(r[8]) if r[8] else None,
        }
        for r in rows
    ]


@router.post("/process")
async def process_invoice(
    request: Request,
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
):
    pool = request.app.state.invoice_pool

    async def event_generator() -> AsyncGenerator[dict, None]:
        raw_text = ""
        file_name = "text-input"

        if file and file.filename:
            file_name = file.filename
            yield {
                "event": "step_start",
                "data": json.dumps({"agent": "doc_reader", "message": f"Reading {file_name}..."}),
            }
            try:
                file_bytes = await file.read()
                raw_text = await read_document(
                    file_bytes, file.content_type or "application/octet-stream", file_name
                )
                yield {
                    "event": "step_complete",
                    "data": json.dumps(
                        {
                            "agent": "doc_reader",
                            "status": "success",
                            "message": f"Extracted {len(raw_text)} characters from {file_name}",
                        }
                    ),
                }
            except Exception as exc:
                yield {
                    "event": "step_complete",
                    "data": json.dumps(
                        {"agent": "doc_reader", "status": "error", "message": str(exc)}
                    ),
                }
                yield {"event": "error", "data": json.dumps({"detail": str(exc)})}
                return
        elif text:
            raw_text = text
            file_name = "pasted-text"
            yield {
                "event": "step_start",
                "data": json.dumps({"agent": "doc_reader", "message": "Processing pasted text..."}),
            }
            yield {
                "event": "step_complete",
                "data": json.dumps(
                    {
                        "agent": "doc_reader",
                        "status": "success",
                        "message": f"Received {len(raw_text)} characters of invoice text",
                    }
                ),
            }
        else:
            yield {"event": "error", "data": json.dumps({"detail": "No file or text provided"})}
            return

        graph = build_invoice_graph(pool)
        input_state = {
            "raw_text": raw_text,
            "file_name": file_name,
            "embedding": [],
            "dedup_vector_result": None,
            "extracted_invoice": None,
            "dedup_exact_result": None,
            "validation_result": None,
            "anomaly_result": None,
            "report": None,
            "current_step": "start",
            "agent_log": [],
        }

        try:
            async for chunk in graph.astream(input_state, stream_mode="updates"):
                for node_name, update in chunk.items():
                    step = update.get("current_step", node_name)
                    logs = update.get("agent_log", [])

                    yield {
                        "event": "step_start",
                        "data": json.dumps({"agent": step, "message": f"Running {step}..."}),
                    }

                    for log_entry in logs:
                        yield {"event": "agent_log", "data": json.dumps(log_entry)}

                    yield {
                        "event": "step_complete",
                        "data": json.dumps(
                            {
                                "agent": step,
                                "status": logs[-1]["status"] if logs else "success",
                                "message": logs[-1]["message"] if logs else "",
                            }
                        ),
                    }

                    if update.get("report"):
                        yield {"event": "final_report", "data": json.dumps(update["report"])}
        except Exception as exc:
            logger.exception("Pipeline error")
            yield {"event": "error", "data": json.dumps({"detail": str(exc)})}
            return

        yield {"event": "done", "data": json.dumps({"status": "complete"})}

    return EventSourceResponse(event_generator())


@router.post("/chat")
async def chat_with_invoices(request: Request, body: ChatRequest):
    pool = request.app.state.invoice_pool

    async def event_generator() -> AsyncGenerator[dict, None]:
        from api.agent.deduplication import embed_text
        from api.config import settings

        try:
            embedding = await embed_text(body.message)
        except Exception:
            embedding = []

        context_parts: list[str] = []

        if embedding:
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            async with pool.connection() as conn:
                cur = await conn.execute(
                    """
                    SELECT invoice_text, invoice_number, vendor_name, total_amount,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM invoice_embeddings
                    ORDER BY embedding <=> %s::vector
                    LIMIT 5
                    """,
                    (embedding_str, embedding_str),
                )
                similar = await cur.fetchall()

            if similar:
                context_parts.append("Similar invoices from vector search:")
                for row in similar:
                    context_parts.append(
                        f"- Invoice {row[1]} from {row[2]}, amount: {row[3]}, "
                        f"similarity: {float(row[4]):.2f}\n  Text preview: {str(row[0])[:300]}"
                    )

        async with pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT invoice_number, vendor_name, total_amount, status,
                       risk_score, currency, processed_at, report_json
                FROM invoice_history
                ORDER BY processed_at DESC
                LIMIT 10
                """
            )
            history = await cur.fetchall()

        if history:
            context_parts.append("\nRecent invoice processing history:")
            for row in history:
                report_data = row[7] or {}
                context_parts.append(
                    f"- {row[0]} from {row[1]}: {row[5]} {float(row[2]) if row[2] else 0:,.2f}, "
                    f"status={row[3]}, risk={row[4]}, processed={row[6]}"
                )
                if isinstance(report_data, dict) and report_data.get("summary"):
                    context_parts.append(f"  Summary: {report_data['summary'][:200]}")

        context = "\n".join(context_parts) if context_parts else "No invoices have been processed yet."

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        stream = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an invoice processing assistant. "
                        "Answer questions about processed invoices using the context below. "
                        "Be concise, accurate, and helpful. Reference specific invoice numbers "
                        "and amounts when relevant. If no data is available, say so."
                    ),
                },
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {body.message}"},
            ],
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"event": "token", "data": json.dumps({"token": delta.content})}

        yield {"event": "done", "data": json.dumps({"status": "complete"})}

    return EventSourceResponse(event_generator())
