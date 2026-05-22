from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import AsyncConnectionPool

from api.agent.checkpointer import create_checkpointer
from api.agent.db import init_invoice_tables
from api.config import settings
from api.routers import agent_router
from api.routers.invoice import router as invoice_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initialising Postgres checkpointer…")
    checkpointer, cp_pool = await create_checkpointer()
    app.state.checkpointer = checkpointer
    logger.info("Checkpointer ready")

    logger.info("Creating invoice connection pool…")
    invoice_pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        max_size=10,
        open=False,
    )
    await invoice_pool.open()
    app.state.invoice_pool = invoice_pool

    try:
        await init_invoice_tables(invoice_pool)
    except Exception:
        logger.exception("Failed to initialize invoice tables — will retry on first request")

    logger.info("Invoice pool ready")

    yield

    logger.info("Shutting down — closing connection pools…")
    await invoice_pool.close()
    await cp_pool.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Pocket CFO — Invoice Processing API",
        version="1.0.0",
        description="Multi-agent invoice processing workflow with pgvector deduplication",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(agent_router)
    app.include_router(invoice_router)

    @app.get("/api/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    @app.get("/api/providers", tags=["providers"])
    async def providers():
        return {
            "providers": ["openai", "mistral"],
            "default": settings.llm_provider,
        }

    return app


app = create_app()
