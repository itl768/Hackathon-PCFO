from __future__ import annotations

import re
from decimal import Decimal

from api.invoicing.domain.extraction import ExtractionResult
from api.invoicing.domain.finding import Finding, Severity

SOURCE_AGENT = "validator"

_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


def validate_extraction(extraction: ExtractionResult | None) -> list[Finding]:
    if extraction is None:
        return []

    findings: list[Finding] = []

    _check_required_scalar(
        findings,
        field_path="invoice_number",
        value=extraction.invoice_number,
        label="Invoice number",
    )
    _check_required_scalar(
        findings,
        field_path="vendor_name",
        value=extraction.vendor_name,
        label="Vendor name",
    )
    if extraction.invoice_date is None:
        findings.append(
            Finding.validation_error(
                field_path="invoice_date",
                message="Invoice date is required",
                source_agent=SOURCE_AGENT,
                severity=Severity.high,
            )
        )
    if extraction.total_amount is None:
        findings.append(
            Finding.validation_error(
                field_path="total_amount",
                message="Total amount is required",
                source_agent=SOURCE_AGENT,
                severity=Severity.high,
            )
        )

    if extraction.due_date is None:
        findings.append(
            Finding.validation_error(
                field_path="due_date",
                message="Due date is not present",
                source_agent=SOURCE_AGENT,
                severity=Severity.medium,
            )
        )
    if extraction.tax_amount is None:
        findings.append(
            Finding.validation_error(
                field_path="tax_amount",
                message="Tax amount is not present",
                source_agent=SOURCE_AGENT,
                severity=Severity.medium,
            )
        )

    if not extraction.line_items:
        findings.append(
            Finding.validation_error(
                field_path="line_items",
                message="At least one line item is required",
                source_agent=SOURCE_AGENT,
                severity=Severity.high,
            )
        )
    else:
        has_named_item = False
        for index, item in enumerate(extraction.line_items):
            if not item.name or not item.name.strip():
                findings.append(
                    Finding.validation_error(
                        field_path="line_items",
                        message=f"Line item {index + 1} has an empty name",
                        source_agent=SOURCE_AGENT,
                        severity=Severity.high,
                    )
                )
            else:
                has_named_item = True
            if item.quantity < Decimal("0"):
                findings.append(
                    Finding.validation_error(
                        field_path="line_items",
                        message=f"Line item {index + 1} has a negative quantity",
                        source_agent=SOURCE_AGENT,
                        severity=Severity.high,
                    )
                )
            if item.unit_price < Decimal("0"):
                findings.append(
                    Finding.validation_error(
                        field_path="line_items",
                        message=f"Line item {index + 1} has a negative unit price",
                        source_agent=SOURCE_AGENT,
                        severity=Severity.high,
                    )
                )
            if item.total < Decimal("0"):
                findings.append(
                    Finding.validation_error(
                        field_path="line_items",
                        message=f"Line item {index + 1} has a negative total",
                        source_agent=SOURCE_AGENT,
                        severity=Severity.high,
                    )
                )
        if not has_named_item and extraction.line_items:
            findings.append(
                Finding.validation_error(
                    field_path="line_items",
                    message="At least one line item must have a name",
                    source_agent=SOURCE_AGENT,
                    severity=Severity.high,
                )
            )

    currency = extraction.currency or ""
    if not _CURRENCY_PATTERN.match(currency):
        findings.append(
            Finding.validation_error(
                field_path="currency",
                message=f"Currency must be a 3-letter ISO code, got '{currency}'",
                source_agent=SOURCE_AGENT,
                severity=Severity.medium,
            )
        )

    try:
        ExtractionResult.model_validate(extraction.model_dump())
    except Exception as exc:
        findings.append(
            Finding.validation_error(
                field_path="_schema",
                message=f"Extraction does not match expected schema: {exc}",
                source_agent=SOURCE_AGENT,
                severity=Severity.high,
            )
        )

    return findings


def _check_required_scalar(
    findings: list[Finding],
    *,
    field_path: str,
    value: str | None,
    label: str,
) -> None:
    if value is None or not str(value).strip():
        findings.append(
            Finding.validation_error(
                field_path=field_path,
                message=f"{label} is required",
                source_agent=SOURCE_AGENT,
                severity=Severity.high,
            )
        )
