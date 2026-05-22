from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["openai", "mistral"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM provider ──────────────────────────────────────────────────────────
    llm_provider: LLMProvider = "openai"
    """Default provider used when no per-request override is supplied."""

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ── Mistral ───────────────────────────────────────────────────────────────
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"

    # ── Postgres ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql://postgres:postgres@localhost:5432/multiagent"

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"

    # ── API server ────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # ── Invoicing ─────────────────────────────────────────────────────────────
    document_storage_path: str = "/var/invoice_documents"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 10
    allowed_mime_types: str = "application/pdf,image/png,image/jpeg"

    # ── Extractor ─────────────────────────────────────────────────────────────
    extractor_image_scale: float = 2.0
    extractor_image_detail: Literal["low", "high", "auto"] = "high"
    extractor_request_timeout_seconds: int = 60
    extractor_max_retries: int = 3

    # ── Review (anomaly / validator / responder) ───────────────────────────────
    review_amount_tolerance: float = 0.02
    responder_model: str = ""
    responder_request_timeout_seconds: int = 30
    responder_max_retries: int = 3

    @property
    def effective_responder_model(self) -> str:
        return self.responder_model or self.openai_model

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def allowed_mime_types_list(self) -> list[str]:
        return [mime.strip() for mime in self.allowed_mime_types.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
