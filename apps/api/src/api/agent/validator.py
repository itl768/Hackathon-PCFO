from __future__ import annotations

from api.agent.date_utils import parse_date
from api.agent.invoice_models import ExtractedInvoice, ValidationResult, ValidationRule

TOLERANCE = 0.02
CENT_TOLERANCE = 0.05


def _approx_equal(a: float, b: float, base: float = 1.0) -> bool:
    return abs(a - b) <= max(CENT_TOLERANCE, TOLERANCE * max(abs(base), 1.0))


def validate_invoice(invoice: ExtractedInvoice) -> ValidationResult:
    rules: list[ValidationRule] = []
    inv_date = parse_date(invoice.invoice_date)
    due_date = parse_date(invoice.due_date)

    if invoice.line_items and invoice.total_amount is not None:
        line_sum = sum(li.line_total for li in invoice.line_items)
        diff = abs(line_sum - invoice.total_amount)
        passed = _approx_equal(line_sum, invoice.total_amount, invoice.total_amount)
        rules.append(
            ValidationRule(
                rule_name="Line Item Totals Match Bill Total",
                passed=passed,
                message=f"Line items sum: {line_sum:.2f}, Bill total: {invoice.total_amount:.2f}"
                + ("" if passed else f" (difference: {diff:.2f})"),
            )
        )
    else:
        rules.append(
            ValidationRule(
                rule_name="Line Item Totals Match Bill Total",
                passed=False,
                message="Missing line items or total amount",
            )
        )

    if invoice.line_items and invoice.vat_total is not None:
        vat_sum = sum(li.vat_amount for li in invoice.line_items)
        passed = _approx_equal(vat_sum, invoice.vat_total, invoice.vat_total)
        rules.append(
            ValidationRule(
                rule_name="VAT Totals Match Line Item VAT",
                passed=passed,
                message=f"Line item VAT sum: {vat_sum:.2f}, Invoice VAT total: {invoice.vat_total:.2f}",
            )
        )
    else:
        rules.append(
            ValidationRule(
                rule_name="VAT Totals Match Line Item VAT",
                passed=invoice.vat_total is None and not invoice.line_items,
                message="VAT total or line items not available for comparison",
            )
        )

    if invoice.vat_total is not None and invoice.total_amount is not None:
        passed = invoice.vat_total < invoice.total_amount
        rules.append(
            ValidationRule(
                rule_name="VAT Below Total Amount",
                passed=passed,
                message=f"VAT: {invoice.vat_total:.2f}, Total: {invoice.total_amount:.2f}",
            )
        )
    else:
        rules.append(
            ValidationRule(
                rule_name="VAT Below Total Amount",
                passed=True,
                message="VAT or total not available — skipped",
            )
        )

    line_check_passed = True
    line_messages: list[str] = []
    for i, li in enumerate(invoice.line_items):
        expected = li.net_amount + li.vat_amount
        if not _approx_equal(expected, li.line_total, li.line_total):
            line_check_passed = False
            line_messages.append(
                f"Line {i + 1}: net({li.net_amount:.2f}) + vat({li.vat_amount:.2f}) != "
                f"total({li.line_total:.2f})"
            )
    rules.append(
        ValidationRule(
            rule_name="Net + VAT = Line Total (per item)",
            passed=line_check_passed if invoice.line_items else False,
            message="; ".join(line_messages) if line_messages else "All line items balanced",
        )
    )

    missing: list[str] = []
    if not invoice.vendor_name:
        missing.append("vendor/seller name")
    if invoice.total_amount is None:
        missing.append("total amount")
    if not invoice.invoice_date:
        missing.append("invoice date")
    rules.append(
        ValidationRule(
            rule_name="Required Fields Present",
            passed=len(missing) == 0,
            message="All required fields present" if not missing else f"Missing: {', '.join(missing)}",
        )
    )

    rules.append(
        ValidationRule(
            rule_name="Invoice Number Present",
            passed=bool(invoice.invoice_number and invoice.invoice_number.strip()),
            message="Invoice number is set"
            if invoice.invoice_number
            else "Invoice number is missing",
        )
    )

    if inv_date and due_date:
        passed = due_date >= inv_date
        rules.append(
            ValidationRule(
                rule_name="Due Date Not Before Invoice Date",
                passed=passed,
                message=f"Due: {due_date.isoformat()}, Invoice: {inv_date.isoformat()}",
            )
        )
    else:
        rules.append(
            ValidationRule(
                rule_name="Due Date Not Before Invoice Date",
                passed=True,
                message="Due date or invoice date missing — skipped",
            )
        )

    if invoice.subtotal is not None and invoice.vat_total is not None and invoice.total_amount is not None:
        expected_total = invoice.subtotal + invoice.vat_total
        passed = _approx_equal(expected_total, invoice.total_amount, invoice.total_amount)
        rules.append(
            ValidationRule(
                rule_name="Subtotal + VAT = Total Amount",
                passed=passed,
                message=f"Subtotal {invoice.subtotal:.2f} + VAT {invoice.vat_total:.2f} "
                f"= {expected_total:.2f}, Total {invoice.total_amount:.2f}",
            )
        )

    net_exceed_passed = True
    net_msgs: list[str] = []
    for i, li in enumerate(invoice.line_items):
        if li.net_amount > li.line_total + CENT_TOLERANCE:
            net_exceed_passed = False
            net_msgs.append(f"Line {i + 1}: net exceeds line total")
    if invoice.line_items:
        rules.append(
            ValidationRule(
                rule_name="Line Net Not Exceed Line Total",
                passed=net_exceed_passed,
                message="; ".join(net_msgs) if net_msgs else "All line nets within totals",
            )
        )

    qty_passed = True
    qty_msgs: list[str] = []
    for i, li in enumerate(invoice.line_items):
        if li.quantity <= 0:
            qty_passed = False
            qty_msgs.append(f"Line {i + 1}: invalid quantity {li.quantity}")
            continue
        expected_net = li.quantity * li.unit_price
        if not _approx_equal(expected_net, li.net_amount, max(li.net_amount, 1)):
            qty_passed = False
            qty_msgs.append(
                f"Line {i + 1}: qty×price {expected_net:.2f} != net {li.net_amount:.2f}"
            )
    if invoice.line_items:
        rules.append(
            ValidationRule(
                rule_name="Quantity × Unit Price ≈ Net (per line)",
                passed=qty_passed,
                message="; ".join(qty_msgs) if qty_msgs else "All line quantity checks passed",
            )
        )

    desc_passed = all(li.description.strip() for li in invoice.line_items) if invoice.line_items else False
    rules.append(
        ValidationRule(
            rule_name="Line Items Have Description",
            passed=desc_passed,
            message="All line items have descriptions"
            if desc_passed
            else "One or more line items missing description",
        )
    )

    if invoice.total_amount is not None:
        rules.append(
            ValidationRule(
                rule_name="Total Amount Is Positive",
                passed=invoice.total_amount > 0,
                message=f"Total amount: {invoice.total_amount:.2f}",
            )
        )

    rules.append(
        ValidationRule(
            rule_name="Currency Present",
            passed=bool(invoice.currency and invoice.currency.strip()),
            message=f"Currency: {invoice.currency or 'missing'}",
        )
    )

    failed = sum(1 for r in rules if not r.passed)
    return ValidationResult(
        rules=rules,
        all_passed=failed == 0,
        failed_count=failed,
    )
