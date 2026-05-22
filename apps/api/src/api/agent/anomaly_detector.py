from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from api.agent.invoice_models import (
    AnomalyFlag,
    AnomalyResult,
    ExtractedInvoice,
    ValidationResult,
)
from api.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a financial fraud and anomaly detection specialist. Analyze the invoice data and validation results to identify suspicious patterns.

Look for:
- Round-number padding (amounts ending in .00 that seem artificial)
- Unusually high amounts for the type of items
- Date anomalies (invoice date in the future, due date before invoice date)
- Missing optional fields that should normally be present
- Vendor name oddities (generic names, special characters)
- Quantity anomalies (unusual quantities)
- Price inconsistencies between similar items
- Potential duplicate indicators

Return a JSON object:
{
  "flags": [
    {
      "flag_type": "string (e.g. 'round_number', 'high_amount', 'date_anomaly')",
      "severity": "low|medium|high",
      "description": "string explaining the concern"
    }
  ],
  "risk_score": number (0-100, where 0=safe, 100=highly suspicious)
}

Return ONLY valid JSON."""


async def detect_anomalies(
    invoice: ExtractedInvoice,
    validation: ValidationResult,
) -> AnomalyResult:
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    context = (
        f"Invoice Data:\n{invoice.model_dump_json(indent=2)}\n\n"
        f"Validation Results:\n{validation.model_dump_json(indent=2)}"
    )

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this invoice for anomalies:\n\n{context}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )

    content = response.choices[0].message.content or '{"flags": [], "risk_score": 0}'
    data = json.loads(content)

    flags = [AnomalyFlag(**f) for f in data.get("flags", [])]

    base_score = data.get("risk_score", 0)
    validation_penalty = validation.failed_count * 15
    risk_score = min(100, int(base_score * 0.6 + validation_penalty * 0.4))

    if risk_score < 30:
        risk_level = "low"
    elif risk_score < 70:
        risk_level = "medium"
    else:
        risk_level = "high"

    return AnomalyResult(
        flags=flags,
        risk_score=risk_score,
        risk_level=risk_level,
    )
