from __future__ import annotations

import json
import logging
from datetime import timedelta

from openai import AsyncOpenAI

from api.agent.date_utils import ALLOWED_FUTURE_DAYS, ALLOWED_PAST_DAYS, parse_date, today, today_iso
from api.agent.invoice_models import (
    AnomalyFlag,
    AnomalyResult,
    ExtractedInvoice,
    ValidationResult,
)
from api.config import settings

logger = logging.getLogger(__name__)

APPROVAL_THRESHOLD_DEFAULT = 10_000.0


def _rule_based_flags(invoice: ExtractedInvoice, validation: ValidationResult) -> list[AnomalyFlag]:
    flags: list[AnomalyFlag] = []
    ref = today()
    inv_date = parse_date(invoice.invoice_date)
    due_date = parse_date(invoice.due_date)
    threshold = getattr(settings, "invoice_approval_threshold", APPROVAL_THRESHOLD_DEFAULT)

    if inv_date and inv_date > ref + timedelta(days=ALLOWED_FUTURE_DAYS):
        flags.append(
            AnomalyFlag(
                flag_type="invoice_date_future",
                severity="high",
                description=(
                    f"Invoice date {inv_date.isoformat()} is beyond {ALLOWED_FUTURE_DAYS} days "
                    f"from today ({ref.isoformat()})"
                ),
            )
        )
    elif inv_date and inv_date > ref:
        flags.append(
            AnomalyFlag(
                flag_type="invoice_date_slightly_future",
                severity="medium",
                description=f"Invoice date {inv_date.isoformat()} is after today ({ref.isoformat()})",
            )
        )

    if inv_date and inv_date < ref - timedelta(days=ALLOWED_PAST_DAYS):
        flags.append(
            AnomalyFlag(
                flag_type="invoice_date_stale",
                severity="medium",
                description=f"Invoice date is older than {ALLOWED_PAST_DAYS} days",
            )
        )

    if inv_date and due_date and due_date < inv_date:
        flags.append(
            AnomalyFlag(
                flag_type="due_date_before_invoice",
                severity="high",
                description="Due date is before invoice date",
            )
        )

    if not due_date:
        flags.append(
            AnomalyFlag(
                flag_type="missing_due_date",
                severity="medium",
                description="Due date is missing — invoice marked incomplete",
            )
        )

    if invoice.total_amount is not None and invoice.total_amount >= threshold:
        flags.append(
            AnomalyFlag(
                flag_type="high_value",
                severity="high",
                description=(
                    f"Total {invoice.currency} {invoice.total_amount:,.2f} exceeds "
                    f"approval threshold {threshold:,.2f}"
                ),
            )
        )

    if invoice.total_amount is not None and invoice.total_amount > 0:
        if invoice.total_amount % 1000 == 0 and invoice.total_amount >= 5000:
            flags.append(
                AnomalyFlag(
                    flag_type="round_number_total",
                    severity="low",
                    description=f"Total amount is a round number ({invoice.total_amount:,.2f})",
                )
            )

    for i, li in enumerate(invoice.line_items):
        if li.quantity <= 0:
            flags.append(
                AnomalyFlag(
                    flag_type="invalid_quantity",
                    severity="high",
                    description=f"Line {i + 1} has non-positive quantity",
                )
            )
        if li.line_total < 0 or li.net_amount < 0:
            flags.append(
                AnomalyFlag(
                    flag_type="negative_line_amount",
                    severity="high",
                    description=f"Line {i + 1} has negative amounts",
                )
            )

    if validation.failed_count >= 2:
        failed_names = [r.rule_name for r in validation.rules if not r.passed]
        flags.append(
            AnomalyFlag(
                flag_type="multiple_validation_failures",
                severity="high",
                description=f"{validation.failed_count} validation rules failed: {', '.join(failed_names[:3])}",
            )
        )

    if not invoice.invoice_number:
        flags.append(
            AnomalyFlag(
                flag_type="missing_invoice_number",
                severity="medium",
                description="Invoice number is missing",
            )
        )

    if invoice.vendor_name and len(invoice.vendor_name.strip()) < 3:
        flags.append(
            AnomalyFlag(
                flag_type="suspicious_vendor_name",
                severity="medium",
                description="Vendor name is unusually short",
            )
        )

    return flags


def _compute_risk_score(flags: list[AnomalyFlag], validation: ValidationResult, llm_score: int) -> int:
    severity_weights = {"low": 8, "medium": 18, "high": 28}
    flag_score = min(60, sum(severity_weights.get(f.severity, 12) for f in flags))
    validation_penalty = min(40, validation.failed_count * 12)
    blended = int(llm_score * 0.35 + flag_score * 0.4 + validation_penalty * 0.25)
    return min(100, blended)


SYSTEM_PROMPT_TEMPLATE = """You are a financial fraud and anomaly detection specialist.

Today's reference date is {today} (use this for all date comparisons — do NOT assume a different year).

Analyze the invoice and validation results. Look for:
- Round-number padding, unusual amounts, date anomalies relative to {today}
- Missing fields, vendor oddities, quantity/price inconsistencies
- Patterns suggesting fraud or data entry errors

Return JSON only:
{{
  "flags": [{{"flag_type": "string", "severity": "low|medium|high", "description": "string"}}],
  "risk_score": 0-100
}}"""


async def detect_anomalies(
    invoice: ExtractedInvoice,
    validation: ValidationResult,
) -> AnomalyResult:
    rule_flags = _rule_based_flags(invoice, validation)

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    ref_today = today_iso()
    context = (
        f"Reference date (today): {ref_today}\n\n"
        f"Invoice Data:\n{invoice.model_dump_json(indent=2)}\n\n"
        f"Validation Results:\n{validation.model_dump_json(indent=2)}\n\n"
        f"Rule-based flags already detected:\n"
        + "\n".join(f"- {f.flag_type}: {f.description}" for f in rule_flags)
        or "(none)"
    )

    llm_flags: list[AnomalyFlag] = []
    llm_score = 0

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_TEMPLATE.replace("{today}", ref_today),
                },
                {"role": "user", "content": f"Analyze this invoice for additional anomalies:\n\n{context}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = response.choices[0].message.content or '{"flags": [], "risk_score": 0}'
        data = json.loads(content)
        llm_score = int(data.get("risk_score", 0))
        seen_types = {f.flag_type for f in rule_flags}
        for f in data.get("flags", []):
            ft = f.get("flag_type", "unknown")
            if ft not in seen_types:
                llm_flags.append(AnomalyFlag(**f))
                seen_types.add(ft)
    except Exception:
        logger.exception("LLM anomaly detection failed, using rule-based only")

    all_flags = rule_flags + llm_flags
    risk_score = _compute_risk_score(all_flags, validation, llm_score)

    if risk_score < 30:
        risk_level = "low"
    elif risk_score < 70:
        risk_level = "medium"
    else:
        risk_level = "high"

    return AnomalyResult(
        flags=all_flags,
        risk_score=risk_score,
        risk_level=risk_level,
    )
