from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from api.agent.currency_utils import normalize_currency
from api.agent.date_utils import today_iso
from api.agent.invoice_models import ExtractedInvoice
from api.agent.prompts import InvoicePrompts
from api.config import settings

logger = logging.getLogger(__name__)


async def extract_invoice(raw_text: str, default_currency: str | None = None) -> ExtractedInvoice:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    ref_today = today_iso()
    currency = normalize_currency(
        default_currency,
        settings.invoice_default_currency,
    )

    system_prompt = InvoicePrompts.extractor_system(ref_today, currency)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt.content},
            {"role": "user", "content": InvoicePrompts.extractor_user(raw_text)},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    if not data.get("currency") or not str(data.get("currency", "")).strip():
        data["currency"] = currency
    else:
        data["currency"] = normalize_currency(str(data["currency"]), currency)
    return ExtractedInvoice(**data)
