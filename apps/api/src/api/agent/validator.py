from __future__ import annotations

from api.agent.invoice_models import ExtractedInvoice, ValidationResult, ValidationRule

TOLERANCE = 0.02


def validate_invoice(invoice: ExtractedInvoice) -> ValidationResult:
    rules: list[ValidationRule] = []

    # Rule 1: Sum of line item totals == bill total
    if invoice.line_items and invoice.total_amount is not None:
        line_sum = sum(li.line_total for li in invoice.line_items)
        diff = abs(line_sum - invoice.total_amount)
        passed = diff <= TOLERANCE * max(invoice.total_amount, 1)
        rules.append(ValidationRule(
            rule_name="Line Item Totals Match Bill Total",
            passed=passed,
            message=f"Line items sum: {line_sum:.2f}, Bill total: {invoice.total_amount:.2f}"
            + ("" if passed else f" (difference: {diff:.2f})"),
        ))
    else:
        rules.append(ValidationRule(
            rule_name="Line Item Totals Match Bill Total",
            passed=False,
            message="Missing line items or total amount",
        ))

    # Rule 2: Sum of line item VAT == invoice VAT total
    if invoice.line_items and invoice.vat_total is not None:
        vat_sum = sum(li.vat_amount for li in invoice.line_items)
        diff = abs(vat_sum - invoice.vat_total)
        passed = diff <= TOLERANCE * max(invoice.vat_total, 1)
        rules.append(ValidationRule(
            rule_name="VAT Totals Match Line Item VAT",
            passed=passed,
            message=f"Line item VAT sum: {vat_sum:.2f}, Invoice VAT total: {invoice.vat_total:.2f}"
            + ("" if passed else f" (difference: {diff:.2f})"),
        ))
    else:
        rules.append(ValidationRule(
            rule_name="VAT Totals Match Line Item VAT",
            passed=invoice.vat_total is None and not invoice.line_items,
            message="VAT total or line items not available for comparison",
        ))

    # Rule 3: VAT < total amount
    if invoice.vat_total is not None and invoice.total_amount is not None:
        passed = invoice.vat_total < invoice.total_amount
        rules.append(ValidationRule(
            rule_name="VAT Below Total Amount",
            passed=passed,
            message=f"VAT: {invoice.vat_total:.2f}, Total: {invoice.total_amount:.2f}",
        ))
    else:
        rules.append(ValidationRule(
            rule_name="VAT Below Total Amount",
            passed=True,
            message="VAT or total not available — skipped",
        ))

    # Rule 4: Net + VAT == line total for each line item
    line_check_passed = True
    line_messages = []
    for i, li in enumerate(invoice.line_items):
        expected = li.net_amount + li.vat_amount
        diff = abs(expected - li.line_total)
        if diff > TOLERANCE * max(li.line_total, 1):
            line_check_passed = False
            line_messages.append(
                f"Line {i + 1}: net({li.net_amount:.2f}) + vat({li.vat_amount:.2f}) = "
                f"{expected:.2f} != total({li.line_total:.2f})"
            )
    if not invoice.line_items:
        rules.append(ValidationRule(
            rule_name="Net + VAT = Line Total (per item)",
            passed=False,
            message="No line items to validate",
        ))
    else:
        rules.append(ValidationRule(
            rule_name="Net + VAT = Line Total (per item)",
            passed=line_check_passed,
            message="; ".join(line_messages) if line_messages else "All line items balanced",
        ))

    # Rule 5: Required fields present (total, seller name, date)
    missing = []
    if not invoice.vendor_name:
        missing.append("vendor/seller name")
    if invoice.total_amount is None:
        missing.append("total amount")
    if not invoice.invoice_date:
        missing.append("invoice date")
    rules.append(ValidationRule(
        rule_name="Required Fields Present",
        passed=len(missing) == 0,
        message="All required fields present" if not missing else f"Missing: {', '.join(missing)}",
    ))

    failed = sum(1 for r in rules if not r.passed)
    return ValidationResult(
        rules=rules,
        all_passed=failed == 0,
        failed_count=failed,
    )
