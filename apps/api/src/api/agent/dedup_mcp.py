from __future__ import annotations

import logging

from api.agent.invoice_models import DuplicationResult, ExtractedInvoice

logger = logging.getLogger(__name__)

AMOUNT_TOLERANCE = 0.01


async def check_exact_duplicate(
    pool,
    invoice: ExtractedInvoice,
    *,
    file_name: str = "",
    content_hash: str = "",
) -> DuplicationResult:
    async with pool.connection() as conn:
        if content_hash:
            row = await conn.execute(
                """
                SELECT id, invoice_number, vendor_name, total_amount
                FROM invoice_history
                WHERE file_hash = %s
                LIMIT 1
                """,
                (content_hash,),
            )
            result = await row.fetchone()
            if result is not None:
                return DuplicationResult(
                    is_duplicate=True,
                    similarity_score=1.0,
                    matched_invoice_id=result[0],
                    matched_invoice_number=result[1],
                    method="file_hash",
                )

        inv_num = (invoice.invoice_number or "").strip()
        vendor = (invoice.vendor_name or "").strip()
        inv_date = (invoice.invoice_date or "").strip()
        total = invoice.total_amount
        fname = (file_name or "").strip()

        if inv_num and vendor and inv_date and total is not None:
            row = await conn.execute(
                """
                SELECT id, invoice_number, vendor_name, total_amount
                FROM invoice_history
                WHERE invoice_number = %s
                  AND LOWER(TRIM(vendor_name)) = LOWER(%s)
                  AND TRIM(invoice_date) = %s
                  AND ABS(total_amount - %s) <= %s
                LIMIT 1
                """,
                (inv_num, vendor, inv_date, total, AMOUNT_TOLERANCE),
            )
            result = await row.fetchone()
            if result is not None:
                return DuplicationResult(
                    is_duplicate=True,
                    similarity_score=1.0,
                    matched_invoice_id=result[0],
                    matched_invoice_number=result[1],
                    method="fields",
                )

        if fname and inv_date and total is not None:
            row = await conn.execute(
                """
                SELECT id, invoice_number, vendor_name, total_amount
                FROM invoice_history
                WHERE file_name = %s
                  AND TRIM(invoice_date) = %s
                  AND ABS(total_amount - %s) <= %s
                LIMIT 1
                """,
                (fname, inv_date, total, AMOUNT_TOLERANCE),
            )
            result = await row.fetchone()
            if result is not None:
                return DuplicationResult(
                    is_duplicate=True,
                    similarity_score=1.0,
                    matched_invoice_id=result[0],
                    matched_invoice_number=result[1],
                    method="filename",
                )

    return DuplicationResult(is_duplicate=False, method="exact")


async def store_in_history(
    pool,
    invoice: ExtractedInvoice,
    status: str,
    risk_score: int,
    report_json: dict,
    *,
    file_hash: str = "",
    file_name: str = "",
) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO invoice_history
                (invoice_number, vendor_name, total_amount, vat_total,
                 invoice_date, currency, status, risk_score, report_json,
                 file_hash, file_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
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
                file_hash or None,
                file_name or None,
            ),
        )
        await conn.commit()
