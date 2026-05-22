from __future__ import annotations

import json

from api.agent.invoice_models import ExtractedInvoice, InvoiceHistoryDetail, InvoiceHistoryUpdate, LineItem


def _row_to_line_item(row: tuple) -> LineItem:
    return LineItem(
        id=row[0],
        gl_account=row[2],
        description=row[3] or "",
        quantity=float(row[4]) if row[4] is not None else 1.0,
        unit_price=float(row[5]) if row[5] is not None else 0.0,
        net_amount=float(row[6]) if row[6] is not None else 0.0,
        vat_rate=float(row[7]) if row[7] is not None else None,
        vat_amount=float(row[8]) if row[8] is not None else 0.0,
        line_total=float(row[9]) if row[9] is not None else 0.0,
    )


async def insert_line_items(conn, invoice_id: int, items: list[LineItem]) -> None:
    for i, item in enumerate(items):
        await conn.execute(
            """
            INSERT INTO invoice_line_items
                (invoice_id, line_order, gl_account, description, quantity,
                 unit_price, net_amount, vat_rate, vat_amount, line_total)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                invoice_id,
                i,
                item.gl_account,
                item.description,
                item.quantity,
                item.unit_price,
                item.net_amount,
                item.vat_rate,
                item.vat_amount,
                item.line_total,
            ),
        )


async def _fetch_source_text(
    conn,
    invoice_number: str | None,
    vendor_name: str | None,
    total_amount: float | None,
) -> str | None:
    if not invoice_number:
        return None
    cur = await conn.execute(
        """
        SELECT invoice_text
        FROM invoice_embeddings
        WHERE invoice_number = %s
          AND (vendor_name IS NOT DISTINCT FROM %s)
          AND (total_amount IS NOT DISTINCT FROM %s)
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (invoice_number, vendor_name, total_amount),
    )
    emb = await cur.fetchone()
    return emb[0] if emb else None


async def get_invoice_detail(pool, invoice_id: int) -> InvoiceHistoryDetail | None:
    async with pool.connection() as conn:
        cur = await conn.execute(
            """
            SELECT id, invoice_number, payment_reference, vendor_name, vendor_iban,
                   vendor_vat_number, vendor_country, vat_reversed, invoice_date,
                   due_date, subtotal, vat_total, total_amount, currency,
                   payment_terms, status, risk_score, file_name, processed_at
            FROM invoice_history
            WHERE id = %s
            """,
            (invoice_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return None

        source_text = await _fetch_source_text(conn, row[1], row[3], row[12])

        cur = await conn.execute(
            """
            SELECT id, line_order, gl_account, description, quantity, unit_price,
                   net_amount, vat_rate, vat_amount, line_total
            FROM invoice_line_items
            WHERE invoice_id = %s
            ORDER BY line_order, id
            """,
            (invoice_id,),
        )
        line_rows = await cur.fetchall()

    return InvoiceHistoryDetail(
        id=row[0],
        invoice_number=row[1],
        payment_reference=row[2],
        vendor_name=row[3],
        vendor_iban=row[4],
        vendor_vat_number=row[5],
        vendor_country=row[6],
        vat_reversed=bool(row[7]),
        invoice_date=row[8],
        due_date=row[9],
        subtotal=float(row[10]) if row[10] is not None else None,
        vat_total=float(row[11]) if row[11] is not None else None,
        total_amount=float(row[12]) if row[12] is not None else None,
        currency=row[13] or "USD",
        payment_terms=row[14],
        status=row[15] or "",
        risk_score=row[16],
        file_name=row[17],
        processed_at=str(row[18]) if row[18] else None,
        source_text=source_text,
        line_items=[_row_to_line_item(r) for r in line_rows],
    )


async def update_invoice(pool, invoice_id: int, body: InvoiceHistoryUpdate) -> InvoiceHistoryDetail | None:
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT id FROM invoice_history WHERE id = %s", (invoice_id,))
        if await cur.fetchone() is None:
            return None

        await conn.execute(
            """
            UPDATE invoice_history SET
                invoice_number = %s,
                payment_reference = %s,
                vendor_name = %s,
                vendor_iban = %s,
                vendor_vat_number = %s,
                vendor_country = %s,
                vat_reversed = %s,
                invoice_date = %s,
                due_date = %s,
                subtotal = %s,
                vat_total = %s,
                total_amount = %s,
                currency = %s,
                payment_terms = %s
            WHERE id = %s
            """,
            (
                body.invoice_number,
                body.payment_reference,
                body.vendor_name,
                body.vendor_iban,
                body.vendor_vat_number,
                body.vendor_country,
                body.vat_reversed,
                body.invoice_date,
                body.due_date,
                body.subtotal,
                body.vat_total,
                body.total_amount,
                body.currency,
                body.payment_terms,
                invoice_id,
            ),
        )
        await conn.execute(
            "DELETE FROM invoice_line_items WHERE invoice_id = %s",
            (invoice_id,),
        )
        await insert_line_items(conn, invoice_id, body.line_items)
        await conn.commit()

    return await get_invoice_detail(pool, invoice_id)


async def store_invoice_with_lines(
    pool,
    invoice: ExtractedInvoice,
    status: str,
    risk_score: int,
    report_json: dict,
    *,
    file_hash: str = "",
    file_name: str = "",
) -> int:
    async with pool.connection() as conn:
        cur = await conn.execute(
            """
            INSERT INTO invoice_history
                (invoice_number, payment_reference, vendor_name, vendor_iban,
                 vendor_vat_number, vendor_country, vat_reversed, invoice_date,
                 due_date, subtotal, vat_total, total_amount, currency,
                 payment_terms, status, risk_score, report_json, file_hash, file_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            RETURNING id
            """,
            (
                invoice.invoice_number,
                invoice.payment_reference,
                invoice.vendor_name,
                invoice.vendor_iban,
                invoice.vendor_vat_number,
                invoice.vendor_country,
                invoice.vat_reversed,
                invoice.invoice_date,
                invoice.due_date,
                invoice.subtotal,
                invoice.vat_total,
                invoice.total_amount,
                invoice.currency,
                invoice.payment_terms,
                status,
                risk_score,
                json.dumps(report_json),
                file_hash or None,
                file_name or None,
            ),
        )
        row = await cur.fetchone()
        invoice_id = row[0]
        await insert_line_items(conn, invoice_id, invoice.line_items)
        await conn.commit()
        return invoice_id
