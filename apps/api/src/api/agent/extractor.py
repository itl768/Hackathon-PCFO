from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from api.agent.currency_utils import normalize_currency
from api.agent.date_utils import today_iso
from api.agent.invoice_models import ExtractedInvoice
from api.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are an expert invoice data extractor. Given raw invoice text, extract the important business fields into structured JSON.

Today's date is {today}. Invoice dates should be YYYY-MM-DD and realistic relative to today.
Default currency if unclear: {default_currency}.

Return JSON with these fields:
{{
  "vendor_name": "supplier company name or null",
  "vendor_iban": "bank IBAN if present or null",
  "vendor_vat_number": "supplier VAT/tax ID if present or null",
  "vendor_country": "supplier country or null",
  "vat_reversed": false,
  "invoice_number": "invoice number or null",
  "payment_reference": "payment reference / structured payment id or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "line_items": [
    {{
      "gl_account": "general ledger / cost category if inferable else null",
      "description": "line description",
      "quantity": 1,
      "unit_price": 0,
      "net_amount": 0,
      "vat_rate": 0,
      "vat_amount": 0,
      "line_total": 0
    }}
  ],
  "subtotal": null,
  "vat_total": null,
  "total_amount": null,
  "currency": "3-letter ISO code",
  "payment_terms": "e.g. Net 30 or null"
}}

Rules:
- Extract EVERY line item (description, net amount excl. VAT, VAT rate %, VAT amount, line total)
- vat_rate is percentage number (e.g. 21 for 21%, 0 for reverse-charge/zero-rated)
- vat_reversed: true only if invoice explicitly indicates reverse charge / VAT shifted
- Use numbers not strings for money fields
- null for missing optional fields
- Return ONLY valid JSON"""


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
