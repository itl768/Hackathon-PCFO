from __future__ import annotations

import hashlib
import logging

from openai import AsyncOpenAI

from api.agent.invoice_models import DuplicationResult
from api.config import settings

logger = logging.getLogger(__name__)


def compute_content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def check_file_hash_duplicate(pool, content_hash: str) -> DuplicationResult:
    if not content_hash:
        return DuplicationResult(is_duplicate=False, method="file_hash")

    async with pool.connection() as conn:
        row = await conn.execute(
            """
            SELECT id, invoice_number, vendor_name
            FROM invoice_history
            WHERE file_hash = %s
            LIMIT 1
            """,
            (content_hash,),
        )
        result = await row.fetchone()

    if result is None:
        return DuplicationResult(is_duplicate=False, method="file_hash")

    return DuplicationResult(
        is_duplicate=True,
        similarity_score=1.0,
        matched_invoice_id=result[0],
        matched_invoice_number=result[1],
        method="file_hash",
    )


async def embed_text(text: str) -> list[float]:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000],
    )
    return response.data[0].embedding


async def store_embedding(pool, text: str, embedding: list[float], metadata: dict) -> None:
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO invoice_embeddings (invoice_text, embedding, invoice_number, vendor_name, total_amount)
            VALUES (%s, %s::vector, %s, %s, %s)
            """,
            (
                text[:10000],
                embedding_str,
                metadata.get("invoice_number"),
                metadata.get("vendor_name"),
                metadata.get("total_amount"),
            ),
        )
        await conn.commit()
