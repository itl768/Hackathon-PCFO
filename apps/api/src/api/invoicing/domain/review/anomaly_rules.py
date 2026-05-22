from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from api.invoicing.domain.extraction import ExtractionResult
from api.invoicing.domain.finding import Finding, Severity

SOURCE_AGENT = "anomaly_detector"


def detect_anomalies(
    extraction: ExtractionResult | None,
    *,
    tolerance: float,
) -> list[Finding]:
    if extraction is None:
        return []

    findings: list[Finding] = []
    today = datetime.now(UTC).date()
    tol = Decimal(str(tolerance))

    if extraction.invoice_date is not None and extraction.invoice_date > today:
        findings.append(
            Finding.anomaly(
                field_path="invoice_date",
                message=f"Invoice date {extraction.invoice_date.isoformat()} is in the future",
                source_agent=SOURCE_AGENT,
                severity=Severity.medium,
            )
        )

    if extraction.due_date is not None and extraction.due_date < today:
        findings.append(
            Finding.anomaly(
                field_path="due_date",
                message=f"Due date {extraction.due_date.isoformat()} is in the past",
                source_agent=SOURCE_AGENT,
                severity=Severity.medium,
            )
        )

    if not extraction.line_items:
        findings.append(
            Finding.anomaly(
                field_path="line_items",
                message="Invoice has no line items",
                source_agent=SOURCE_AGENT,
                severity=Severity.high,
            )
        )

    if extraction.total_amount is not None and extraction.line_items:
        line_sum = sum((item.total for item in extraction.line_items), Decimal("0"))
        delta = abs(line_sum - extraction.total_amount)
        if delta > tol:
            findings.append(
                Finding.anomaly(
                    field_path="total_amount",
                    message=(
                        f"Line item totals ({line_sum}) do not match invoice total "
                        f"({extraction.total_amount}); difference {delta}"
                    ),
                    source_agent=SOURCE_AGENT,
                    severity=Severity.high,
                )
            )

    return findings
