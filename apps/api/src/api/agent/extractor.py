from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from api.agent.currency_utils import normalize_currency
from api.agent.date_utils import today_iso
from api.agent.invoice_models import ExtractedInvoice
from api.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are an expert invoice data extractor. Given raw invoice text, extract ALL fields into structured JSON.

Today's date is {today}. Use this when interpreting relative dates. Invoice dates should be realistic relative to today.

The system's default currency is {default_currency}. If the invoice does not clearly state a currency, use {default_currency}.

Return a JSON object with these exact fields:
{
  "vendor_name": "string or null",
  "invoice_number": "string or null",
  "invoice_date": "string (YYYY-MM-DD) or null",
  "due_date": "string (YYYY-MM-DD) or null",
  "line_items": [
    {
      "description": "string",
      "quantity": number,
      "unit_price": number,
      "net_amount": number (price before VAT/tax),
      "vat_amount": number (VAT/tax for this line),
      "line_total": number (net + vat, total for this line)
    }
  ],
  "subtotal": number or null (sum before tax),
  "vat_total": number or null (total VAT/tax amount),
  "total_amount": number or null (final total including tax),
  "currency": "string (e.g. USD, EUR, GBP)",
  "payment_terms": "string or null"
}

Rules:
- Extract EVERY line item with per-item net, VAT, and total
- If VAT is not explicitly listed per line, estimate from overall VAT rate
- Use numbers (not strings) for all monetary values
- If a field is not found, use null
- Currency should be a 3-letter ISO code (USD, EUR, GBP, LKR, etc.)
- Return ONLY valid JSON, no markdown or explanations"""


async def extract_invoice(raw_text: str, default_currency: str | None = None) -> ExtractedInvoice:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    ref_today = today_iso()
    currency = normalize_currency(
        default_currency,
        settings.invoice_default_currency,
    )

    system = (
        SYSTEM_PROMPT_TEMPLATE.replace("{today}", ref_today).replace(
            "{default_currency}", currency
        )
    )

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Extract all fields from this invoice:\n\n{raw_text}"},
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
