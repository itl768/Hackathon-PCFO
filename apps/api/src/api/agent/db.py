from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_HISTORY_ALTER_COLUMNS = [
    ("due_date", "TEXT"),
    ("payment_reference", "TEXT"),
    ("vendor_iban", "TEXT"),
    ("vendor_vat_number", "TEXT"),
    ("vendor_country", "TEXT"),
    ("vat_reversed", "BOOLEAN DEFAULT FALSE"),
    ("subtotal", "NUMERIC(12,2)"),
    ("payment_terms", "TEXT"),
]


async def init_invoice_tables(pool) -> None:
    async with pool.connection() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS invoice_embeddings (
                id SERIAL PRIMARY KEY,
                invoice_text TEXT NOT NULL,
                embedding vector(1536) NOT NULL,
                invoice_number TEXT,
                vendor_name TEXT,
                total_amount NUMERIC(12,2),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS invoice_history (
                id SERIAL PRIMARY KEY,
                invoice_number TEXT,
                vendor_name TEXT,
                total_amount NUMERIC(12,2),
                vat_total NUMERIC(12,2),
                invoice_date TEXT,
                due_date TEXT,
                currency TEXT DEFAULT 'USD',
                status TEXT NOT NULL,
                risk_score INTEGER,
                report_json JSONB,
                file_hash TEXT,
                file_name TEXT,
                payment_reference TEXT,
                vendor_iban TEXT,
                vendor_vat_number TEXT,
                vendor_country TEXT,
                vat_reversed BOOLEAN DEFAULT FALSE,
                subtotal NUMERIC(12,2),
                payment_terms TEXT,
                processed_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        for col, col_type in _HISTORY_ALTER_COLUMNS:
            await conn.execute(
                f"ALTER TABLE invoice_history ADD COLUMN IF NOT EXISTS {col} {col_type}"
            )
        await conn.execute(
            "ALTER TABLE invoice_history ADD COLUMN IF NOT EXISTS file_hash TEXT"
        )
        await conn.execute(
            "ALTER TABLE invoice_history ADD COLUMN IF NOT EXISTS file_name TEXT"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS invoice_line_items (
                id SERIAL PRIMARY KEY,
                invoice_id INTEGER NOT NULL REFERENCES invoice_history(id) ON DELETE CASCADE,
                line_order INTEGER NOT NULL DEFAULT 0,
                gl_account TEXT,
                description TEXT NOT NULL DEFAULT '',
                quantity NUMERIC(12,4) DEFAULT 1,
                unit_price NUMERIC(12,2) DEFAULT 0,
                net_amount NUMERIC(12,2) DEFAULT 0,
                vat_rate NUMERIC(5,2),
                vat_amount NUMERIC(12,2) DEFAULT 0,
                line_total NUMERIC(12,2) DEFAULT 0
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_invoice_history_file_hash ON invoice_history (file_hash)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice_id ON invoice_line_items (invoice_id)"
        )
        await conn.commit()
    logger.info("Invoice tables initialized (history, line_items, embeddings)")
