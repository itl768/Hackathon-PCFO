from __future__ import annotations

import json
import logging
from datetime import timedelta

from openai import AsyncOpenAI

from api.agent.date_utils import (
    ALLOWED_FUTURE_DAYS,
    ALLOWED_PAST_DAYS,
    STALE_INVOICE_DAYS,
    is_before_reference,
    is_more_than_days_before_reference,
    parse_date,
    today,
    today_iso,
)
from api.agent.invoice_models import (
    AnomalyFlag,
    AnomalyResult,
    ExtractedInvoice,
    ValidationResult,
)
from api.agent.prompts import InvoicePrompts
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

    if inv_date and is_more_than_days_before_reference(inv_date, ALLOWED_PAST_DAYS, ref):
        flags.append(
            AnomalyFlag(
                flag_type="invoice_date_stale",
                severity="medium",
                description=f"Invoice date is older than {ALLOWED_PAST_DAYS} days",
            )
        )
    elif inv_date and is_more_than_days_before_reference(inv_date, STALE_INVOICE_DAYS, ref):
        flags.append(
            AnomalyFlag(
                flag_type="invoice_date_old",
                severity="medium",
                description=(
                    f"Invoice date {inv_date.isoformat()} is more than one year before today "
                    f"({ref.isoformat()})"
                ),
            )
        )

    if due_date and is_before_reference(due_date, ref):
        flags.append(
            AnomalyFlag(
                flag_type="due_date_overdue",
                severity="medium",
                description=(
                    f"Due date {due_date.isoformat()} has passed (today is {ref.isoformat()})"
                ),
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

    return flags


def _is_discarded_vendor_flag(flag: AnomalyFlag) -> bool:
    text = flag.description.lower()
    ft = flag.flag_type.lower()
    if "vendor" not in text and "vendor" not in ft:
        return False
    discarded = (
        "generic",
        "non-specific",
        "non specific",
        "unspecific",
        "not specific",
        "vague",
        "unusually short",
        "too short",
        "suspicious_vendor",
    )
    return any(kw in text or kw in ft for kw in discarded)


def _filter_llm_date_flags(
    llm_flags: list[AnomalyFlag],
    invoice: ExtractedInvoice,
    ref: date,
) -> list[AnomalyFlag]:
    inv_date = parse_date(invoice.invoice_date)
    due_date = parse_date(invoice.due_date)
    filtered: list[AnomalyFlag] = []

    for flag in llm_flags:
        text = flag.description.lower()
        if due_date and "due" in text and "future" in text:
            continue
        if due_date and due_date > ref and "due" in text and (
            "overdue" in text or "passed" in text or "past due" in text
        ):
            continue
        if inv_date and inv_date <= ref and "invoice" in text and "future" in text:
            continue
        if _is_discarded_vendor_flag(flag):
            continue
        filtered.append(flag)

    return filtered


def _compute_risk_score(flags: list[AnomalyFlag], validation: ValidationResult, llm_score: int) -> int:
    severity_weights = {"low": 8, "medium": 18, "high": 28}
    flag_score = min(60, sum(severity_weights.get(f.severity, 12) for f in flags))
    validation_penalty = min(40, validation.failed_count * 12)
    blended = int(llm_score * 0.35 + flag_score * 0.4 + validation_penalty * 0.25)
    return min(100, blended)


async def detect_anomalies(
    invoice: ExtractedInvoice,
    validation: ValidationResult,
) -> AnomalyResult:
    ref = today()
    rule_flags = _rule_based_flags(invoice, validation)

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    ref_today = ref.isoformat()
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
        system_prompt = InvoicePrompts.anomaly_system(ref_today)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt.content},
                {"role": "user", "content": InvoicePrompts.anomaly_user(context)},
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
        llm_flags = _filter_llm_date_flags(llm_flags, invoice, ref)
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
