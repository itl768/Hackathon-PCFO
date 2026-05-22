from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from api.agent.invoice_models import ExtractedInvoice
from api.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert invoice data extractor. Given raw invoice text, extract ALL fields into structured JSON.

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
- Currency should be the ISO code (USD, EUR, GBP, etc.)
- Return ONLY valid JSON, no markdown or explanations"""


async def extract_invoice(raw_text: str) -> ExtractedInvoice:
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract all fields from this invoice:\n\n{raw_text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    return ExtractedInvoice(**data)
