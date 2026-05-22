from __future__ import annotations

from api.agent.invoice_models import (
    AnomalyResult,
    ApprovalStatus,
    DuplicationResult,
    ExtractedInvoice,
    ProcessingReport,
    ValidationResult,
)


def generate_report(
    extracted: ExtractedInvoice,
    dedup_vector: DuplicationResult,
    dedup_exact: DuplicationResult,
    validation: ValidationResult,
    anomalies: AnomalyResult,
) -> ProcessingReport:
    if dedup_vector.is_duplicate or dedup_exact.is_duplicate:
        dup_source = dedup_vector if dedup_vector.is_duplicate else dedup_exact
        decision = ApprovalStatus.DUPLICATE_REJECT.value
        confidence = "high"
        summary = (
            f"Duplicate invoice detected via {dup_source.method} matching "
            f"(similarity: {dup_source.similarity_score:.2f}, "
            f"matched: {dup_source.matched_invoice_number or 'N/A'}). "
            f"Invoice from {extracted.vendor_name or 'Unknown'} rejected."
        )
        next_steps = [
            "Review the matched original invoice",
            "Confirm with vendor if this is a legitimate resubmission",
            "Archive this duplicate",
        ]
    elif validation.all_passed and anomalies.risk_score < 30:
        decision = ApprovalStatus.AUTO_APPROVE.value
        confidence = "high"
        summary = (
            f"Invoice {extracted.invoice_number or 'N/A'} from "
            f"{extracted.vendor_name or 'Unknown'} for "
            f"{extracted.currency} {extracted.total_amount or 0:,.2f} "
            f"passed all validation checks with low risk (score: {anomalies.risk_score})."
        )
        next_steps = [
            "Process payment according to payment terms",
            f"Due date: {extracted.due_date or 'Not specified'}",
        ]
    elif anomalies.risk_score > 70 or validation.failed_count >= 3:
        decision = ApprovalStatus.REJECT.value
        confidence = "high" if anomalies.risk_score > 85 else "medium"
        failed_rules = [r.rule_name for r in validation.rules if not r.passed]
        summary = (
            f"Invoice {extracted.invoice_number or 'N/A'} from "
            f"{extracted.vendor_name or 'Unknown'} rejected. "
            f"Risk score: {anomalies.risk_score}/100. "
            f"Failed validations: {', '.join(failed_rules) if failed_rules else 'None'}."
        )
        next_steps = [
            "Return to vendor for correction",
            "Escalate to finance manager for review",
            "Request supporting documentation",
        ]
    else:
        decision = ApprovalStatus.MANUAL_REVIEW.value
        confidence = "medium"
        failed_rules = [r.rule_name for r in validation.rules if not r.passed]
        flag_types = [f.flag_type for f in anomalies.flags]
        summary = (
            f"Invoice {extracted.invoice_number or 'N/A'} from "
            f"{extracted.vendor_name or 'Unknown'} requires manual review. "
            f"Risk score: {anomalies.risk_score}/100. "
            f"Issues: {', '.join(failed_rules + flag_types) if (failed_rules or flag_types) else 'Minor concerns'}."
        )
        next_steps = [
            "Review flagged anomalies manually",
            "Verify amounts with vendor",
            "Approve or reject after review",
        ]

    return ProcessingReport(
        summary=summary,
        agent_outputs={
            "document_reader": "Text extracted successfully",
            "dedup_vector": dedup_vector.model_dump(),
            "extractor": {"fields_extracted": len(extracted.model_fields_set)},
            "dedup_exact": dedup_exact.model_dump(),
            "validator": {"passed": validation.all_passed, "failed_count": validation.failed_count},
            "anomaly_detector": {"risk_score": anomalies.risk_score, "flags": len(anomalies.flags)},
        },
        decision=decision,
        recommendation=decision,
        confidence=confidence,
        risk_score=anomalies.risk_score,
        next_steps=next_steps,
        extracted_invoice=extracted,
        dedup_vector=dedup_vector,
        dedup_exact=dedup_exact,
        validation=validation,
        anomalies=anomalies,
    )
