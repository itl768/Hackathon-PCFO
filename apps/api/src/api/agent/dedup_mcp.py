from __future__ import annotations

import logging

from api.agent.invoice_models import DuplicationResult, ExtractedInvoice

logger = logging.getLogger(__name__)


async def check_exact_duplicate(pool, invoice: ExtractedInvoice) -> DuplicationResult:
    if not invoice.invoice_number and not invoice.vendor_name:
        return DuplicationResult(is_duplicate=False, method="exact")

    async with pool.connection() as conn:
        if invoice.invoice_number and invoice.vendor_name:
            row = await conn.execute(
                """
                SELECT id, invoice_number, vendor_name, total_amount
                FROM invoice_history
                WHERE invoice_number = %s AND LOWER(vendor_name) = LOWER(%s)
                LIMIT 1
                """,
                (invoice.invoice_number, invoice.vendor_name),
            )
        elif invoice.invoice_number:
            row = await conn.execute(
                """
                SELECT id, invoice_number, vendor_name, total_amount
                FROM invoice_history
                WHERE invoice_number = %s
                LIMIT 1
                """,
                (invoice.invoice_number,),
            )
        else:
            row = await conn.execute(
                """
                SELECT id, invoice_number, vendor_name, total_amount
                FROM invoice_history
                WHERE LOWER(vendor_name) = LOWER(%s)
                AND ABS(total_amount - %s) / GREATEST(total_amount, 0.01) < 0.01
                LIMIT 1
                """,
                (invoice.vendor_name, invoice.total_amount or 0),
            )

        result = await row.fetchone()

    if result is None:
        return DuplicationResult(is_duplicate=False, method="exact")

    return DuplicationResult(
        is_duplicate=True,
        similarity_score=1.0,
        matched_invoice_id=result[0],
        matched_invoice_number=result[1],
        method="exact",
    )


async def store_in_history(pool, invoice: ExtractedInvoice, status: str, risk_score: int, report_json: dict) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO invoice_history
                (invoice_number, vendor_name, total_amount, vat_total,
                 invoice_date, currency, status, risk_score, report_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                invoice.invoice_number,
                invoice.vendor_name,
                invoice.total_amount,
                invoice.vat_total,
                invoice.invoice_date,
                invoice.currency,
                status,
                risk_score,
                __import__("json").dumps(report_json),
            ),
        )
        await conn.commit()
