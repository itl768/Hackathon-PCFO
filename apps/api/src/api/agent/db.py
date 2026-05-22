from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


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
                currency TEXT DEFAULT 'USD',
                status TEXT NOT NULL,
                risk_score INTEGER,
                report_json JSONB,
                file_hash TEXT,
                file_name TEXT,
                processed_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute(
            "ALTER TABLE invoice_history ADD COLUMN IF NOT EXISTS file_hash TEXT"
        )
        await conn.execute(
            "ALTER TABLE invoice_history ADD COLUMN IF NOT EXISTS file_name TEXT"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_invoice_history_file_hash ON invoice_history (file_hash)"
        )
        await conn.commit()
    logger.info("Invoice tables initialized (invoice_embeddings + invoice_history)")
