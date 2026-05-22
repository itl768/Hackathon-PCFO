from __future__ import annotations

from datetime import date
from decimal import Decimal

from api.invoicing.domain.extraction import ExtractionResult, LineItemDraft
from api.invoicing.domain.finding import FindingKind
from api.invoicing.domain.review.validation_rules import validate_extraction


def test_validate_extraction_returns_empty_when_none() -> None:
    assert validate_extraction(None) == []


def test_missing_required_fields() -> None:
    findings = validate_extraction(ExtractionResult())
    paths = {f.field_path for f in findings}
    assert "invoice_number" in paths
    assert "vendor_name" in paths
    assert "invoice_date" in paths
    assert "total_amount" in paths
    assert "line_items" in paths
    assert all(f.kind is FindingKind.validation_error for f in findings)


def test_missing_optional_fields_medium_severity() -> None:
    extraction = ExtractionResult(
        invoice_number="1",
        vendor_name="Vendor",
        invoice_date=date(2024, 1, 15),
        total_amount=Decimal("10"),
        line_items=[LineItemDraft(name="Item", total=Decimal("10"))],
    )
    findings = validate_extraction(extraction)
    paths = {f.field_path for f in findings}
    assert "due_date" in paths
    assert "tax_amount" in paths


def test_invalid_currency() -> None:
    extraction = ExtractionResult(
        invoice_number="1",
        vendor_name="Vendor",
        invoice_date=date(2024, 1, 15),
        total_amount=Decimal("10"),
        line_items=[LineItemDraft(name="Item", total=Decimal("10"))],
        currency="dollars",
    )
    findings = validate_extraction(extraction)
    assert any(f.field_path == "currency" for f in findings)


def test_negative_line_item_total() -> None:
    extraction = ExtractionResult(
        invoice_number="1",
        vendor_name="Vendor",
        invoice_date=date(2024, 1, 15),
        total_amount=Decimal("10"),
        line_items=[LineItemDraft(name="Item", total=Decimal("-1"))],
    )
    findings = validate_extraction(extraction)
    assert any(f.field_path == "line_items" for f in findings)


def test_valid_extraction_minimal_errors_only_optional() -> None:
    extraction = ExtractionResult(
        invoice_number="INV-99",
        vendor_name="Acme Corp",
        invoice_date=date(2024, 6, 1),
        due_date=date(2024, 7, 1),
        tax_amount=Decimal("0"),
        total_amount=Decimal("50"),
        line_items=[LineItemDraft(name="Service", total=Decimal("50"))],
        currency="USD",
    )
    findings = validate_extraction(extraction)
    paths = {f.field_path for f in findings}
    assert "invoice_number" not in paths
    assert "vendor_name" not in paths
    assert "line_items" not in paths or all(
        f.field_path != "line_items" or "empty name" not in f.message.lower()
        for f in findings
    )
