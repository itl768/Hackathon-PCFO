from __future__ import annotations

import logging

from openai import AsyncOpenAI

from api.agent.invoice_models import DuplicationResult
from api.config import settings

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.92


async def embed_text(text: str) -> list[float]:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000],
    )
    return response.data[0].embedding


async def check_vector_duplicate(pool, embedding: list[float]) -> DuplicationResult:
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    async with pool.connection() as conn:
        row = await conn.execute(
            """
            SELECT id, invoice_number, vendor_name,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM invoice_embeddings
            ORDER BY embedding <=> %s::vector
            LIMIT 1
            """,
            (embedding_str, embedding_str),
        )
        result = await row.fetchone()

    if result is None:
        return DuplicationResult(
            is_duplicate=False,
            similarity_score=0.0,
            method="vector",
        )

    similarity = float(result[3])
    return DuplicationResult(
        is_duplicate=similarity >= SIMILARITY_THRESHOLD,
        similarity_score=round(similarity, 4),
        matched_invoice_id=result[0],
        matched_invoice_number=result[1],
        method="vector",
    )


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
