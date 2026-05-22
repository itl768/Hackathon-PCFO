from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from api.agent.checkpointer import create_checkpointer
from api.config import settings
from api.invoicing.agents.runner import LangGraphPipelineRunner
from api.invoicing.application.get_invoice import GetInvoice
from api.invoicing.application.process_invoice import ProcessInvoice
from api.invoicing.infrastructure.documents.local_document_store import LocalDocumentStore
from api.invoicing.infrastructure.extraction import OpenAIExtractionService
from api.invoicing.infrastructure.summary import OpenAIReviewSummaryService
from api.invoicing.infrastructure.messaging.in_process_publisher import InProcessEventPublisher
from api.invoicing.infrastructure.persistence import (
    SqlInvoiceRepository,
    create_engine,
    create_session_factory,
    dispose_engine,
)
from api.routers import agent_router, invoicing_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up - initialising Postgres checkpointer and invoicing context...")
    checkpointer, pool = await create_checkpointer()
    app.state.checkpointer = checkpointer

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    app.state.db_engine = engine
    app.state.session_factory = session_factory

    document_store = LocalDocumentStore(settings.document_storage_path)
    app.state.document_store = document_store

    invoice_repository = SqlInvoiceRepository(session_factory)
    app.state.invoice_repository = invoice_repository

    event_publisher = InProcessEventPublisher()
    app.state.event_publisher = event_publisher

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY must be set to run the invoice extraction pipeline"
        )

    openai_client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.extractor_request_timeout_seconds,
    )
    app.state.openai_client = openai_client

    extraction_service = OpenAIExtractionService(
        client=openai_client,
        document_store=document_store,
        model=settings.openai_model,
        image_scale=settings.extractor_image_scale,
        image_detail=settings.extractor_image_detail,
        max_pages=settings.max_pdf_pages,
        max_retries=settings.extractor_max_retries,
        request_timeout_seconds=settings.extractor_request_timeout_seconds,
    )
    app.state.extraction_service = extraction_service

    review_summary_service = OpenAIReviewSummaryService(
        client=openai_client,
        model=settings.effective_responder_model,
        max_retries=settings.responder_max_retries,
        request_timeout_seconds=settings.responder_request_timeout_seconds,
    )
    app.state.review_summary_service = review_summary_service

    pipeline_runner = LangGraphPipelineRunner(
        invoice_repository=invoice_repository,
        event_publisher=event_publisher,
        extraction_service=extraction_service,
        extractor_model_name=settings.openai_model,
        review_summary_service=review_summary_service,
        responder_model_name=settings.effective_responder_model,
        review_amount_tolerance=settings.review_amount_tolerance,
    )
    app.state.pipeline_runner = pipeline_runner

    app.state.process_invoice = ProcessInvoice(
        document_store=document_store,
        invoice_repository=invoice_repository,
        event_publisher=event_publisher,
        pipeline_runner=pipeline_runner,
        allowed_mime_types=settings.allowed_mime_types_list,
        max_upload_bytes=settings.max_upload_bytes,
    )
    app.state.get_invoice = GetInvoice(invoice_repository=invoice_repository)

    logger.info("Invoicing context ready")

    try:
        yield
    finally:
        logger.info("Shutting down - closing connection pools...")
        await pool.close()
        await dispose_engine(engine)
        await openai_client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Invoice Processing Engine API",
        version="0.1.0",
        description="FastAPI + LangGraph invoice processing backend",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(agent_router)
    app.include_router(invoicing_router)

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
