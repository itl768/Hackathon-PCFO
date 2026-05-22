from __future__ import annotations

import base64
import logging
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, ConfigDict
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from api.invoicing.application.ports import DocumentStore, ExtractionService
from api.invoicing.domain import (
    ExtractionFailed,
    ExtractionResult,
    LineItemDraft,
)
from api.invoicing.infrastructure.extraction.pdf_rasteriser import rasterise_pdf

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You extract structured invoice data from one or more page images of the same invoice.

Return JSON that exactly matches the provided schema.

Rules:
- Use ISO-8601 (YYYY-MM-DD) for invoice_date and due_date.
- Use plain decimal numbers for quantity, unit_price, total, total_amount, tax_amount (no currency symbols, no thousand separators).
- If a field is not present on the invoice, return null.
- Include every line item visible in the document, in order. Do not invent items.
- currency should be a 3-letter ISO code (e.g. USD, EUR, INR); if not stated, return "USD".
- vendor_name should be the seller's business name, not the buyer.
"""


class LLMExtractedLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    quantity: float
    unit_price: float
    total: float


class LLMExtractedInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_number: str | None
    vendor_name: str | None
    invoice_date: str | None
    due_date: str | None
    line_items: list[LLMExtractedLineItem]
    total_amount: float | None
    tax_amount: float | None
    currency: str


class OpenAIExtractionService(ExtractionService):
    def __init__(
        self,
        *,
        client: AsyncOpenAI,
        document_store: DocumentStore,
        model: str,
        image_scale: float,
        image_detail: Literal["low", "high", "auto"],
        max_pages: int,
        max_retries: int,
        request_timeout_seconds: int,
    ) -> None:
        self._client = client
        self._document_store = document_store
        self._model = model
        self._image_scale = image_scale
        self._image_detail = image_detail
        self._max_pages = max_pages
        self._max_retries = max_retries
        self._request_timeout_seconds = request_timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    async def extract(
        self,
        *,
        document_uri: str,
        mime_type: str,
        original_filename: str,
    ) -> ExtractionResult:
        document_bytes = await self._document_store.read(document_uri)
        page_images = await self._prepare_page_images(document_bytes, mime_type)

        if not page_images:
            raise ExtractionFailed("No page images produced from document")

        user_content = _build_user_content(page_images, self._image_detail)

        started = time.monotonic()
        parsed = await self._call_openai(user_content)
        latency_ms = int((time.monotonic() - started) * 1000)

        logger.info(
            "Extractor completed in %dms using %s across %d page(s)",
            latency_ms,
            self._model,
            len(page_images),
        )

        return _to_domain(parsed)

    async def _prepare_page_images(self, content: bytes, mime_type: str) -> list[bytes]:
        if mime_type == "application/pdf":
            return await rasterise_pdf(
                content,
                scale=self._image_scale,
                max_pages=self._max_pages,
            )
        if mime_type in {"image/png", "image/jpeg"}:
            return [content]
        raise ExtractionFailed(f"Unsupported mime type for extraction: {mime_type}")

    async def _call_openai(
        self,
        user_content: list[dict[str, Any]],
    ) -> LLMExtractedInvoice:
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(
                (RateLimitError, APITimeoutError, APIConnectionError)
            ),
            reraise=True,
        )

        async for attempt in retrying:
            with attempt:
                try:
                    completion = await self._client.beta.chat.completions.parse(
                        model=self._model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_content},
                        ],
                        response_format=LLMExtractedInvoice,
                        timeout=self._request_timeout_seconds,
                    )
                except (RateLimitError, APITimeoutError, APIConnectionError):
                    raise
                except Exception as exc:
                    logger.exception("Extractor call failed")
                    raise ExtractionFailed(f"Model call failed: {exc}") from exc

                message = completion.choices[0].message
                if message.refusal:
                    raise ExtractionFailed(f"Model refused to extract: {message.refusal}")
                parsed = message.parsed
                if parsed is None:
                    raise ExtractionFailed("Model returned no parsed payload")
                return parsed

        raise ExtractionFailed("Extractor exhausted retries without a response")


def _build_user_content(
    page_images: list[bytes],
    detail: Literal["low", "high", "auto"],
) -> list[dict[str, Any]]:
    instruction = (
        f"Extract invoice fields from the following {len(page_images)} page(s)."
        if len(page_images) > 1
        else "Extract invoice fields from the following page."
    )
    content: list[dict[str, Any]] = [{"type": "text", "text": instruction}]
    for index, image_bytes in enumerate(page_images, start=1):
        encoded = base64.b64encode(image_bytes).decode("ascii")
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{encoded}",
                    "detail": detail,
                },
            }
        )
        content.append({"type": "text", "text": f"Page {index} of {len(page_images)}."})
    return content


def _to_domain(parsed: LLMExtractedInvoice) -> ExtractionResult:
    return ExtractionResult(
        invoice_number=_clean_optional_str(parsed.invoice_number),
        vendor_name=_clean_optional_str(parsed.vendor_name),
        invoice_date=_parse_iso_date(parsed.invoice_date, "invoice_date"),
        due_date=_parse_iso_date(parsed.due_date, "due_date"),
        line_items=[
            LineItemDraft(
                name=item.name.strip(),
                quantity=_to_decimal(item.quantity),
                unit_price=_to_decimal(item.unit_price),
                total=_to_decimal(item.total),
            )
            for item in parsed.line_items
        ],
        total_amount=_optional_decimal(parsed.total_amount),
        tax_amount=_optional_decimal(parsed.tax_amount),
        currency=(parsed.currency or "USD").upper(),
    )


def _clean_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_iso_date(value: str | None, field_name: str) -> date | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return datetime.strptime(cleaned, "%Y-%m-%d").date()
    except ValueError:
        logger.warning("Could not parse %s as ISO date: %s", field_name, value)
        return None


def _to_decimal(value: float) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _optional_decimal(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return _to_decimal(value)
