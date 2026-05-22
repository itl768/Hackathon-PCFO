from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from api.invoicing.domain.extraction import ExtractionResult, LineItemDraft
from api.invoicing.domain.finding import FindingKind
from api.invoicing.domain.review.anomaly_rules import detect_anomalies


def _today() -> date:
    return datetime.now(UTC).date()


def test_detect_anomalies_returns_empty_when_extraction_none() -> None:
    assert detect_anomalies(None, tolerance=0.02) == []


def test_invoice_date_in_future() -> None:
    future = _today() + timedelta(days=30)
    extraction = ExtractionResult(
        invoice_date=future,
        line_items=[LineItemDraft(name="Item", total=Decimal("10"))],
        total_amount=Decimal("10"),
    )
    findings = detect_anomalies(extraction, tolerance=0.02)
    paths = {f.field_path for f in findings}
    assert "invoice_date" in paths
    assert all(f.kind is FindingKind.anomaly for f in findings)


def test_due_date_in_past() -> None:
    past = _today() - timedelta(days=1)
    extraction = ExtractionResult(
        due_date=past,
        line_items=[LineItemDraft(name="Item", total=Decimal("5"))],
        total_amount=Decimal("5"),
    )
    findings = detect_anomalies(extraction, tolerance=0.02)
    assert any(f.field_path == "due_date" for f in findings)


def test_no_line_items() -> None:
    extraction = ExtractionResult(
        invoice_date=_today(),
        line_items=[],
        total_amount=Decimal("100"),
    )
    findings = detect_anomalies(extraction, tolerance=0.02)
    assert any(f.field_path == "line_items" for f in findings)


def test_line_items_total_mismatch() -> None:
    extraction = ExtractionResult(
        line_items=[
            LineItemDraft(name="A", total=Decimal("40")),
            LineItemDraft(name="B", total=Decimal("50")),
        ],
        total_amount=Decimal("100"),
    )
    findings = detect_anomalies(extraction, tolerance=0.02)
    assert any(f.field_path == "total_amount" for f in findings)


def test_line_items_total_within_tolerance() -> None:
    extraction = ExtractionResult(
        line_items=[LineItemDraft(name="A", total=Decimal("50.01"))],
        total_amount=Decimal("50"),
    )
    findings = detect_anomalies(extraction, tolerance=0.02)
    assert not any(f.field_path == "total_amount" for f in findings)


def test_clean_invoice_has_no_anomalies() -> None:
    today = _today()
    extraction = ExtractionResult(
        invoice_number="INV-1",
        vendor_name="Acme",
        invoice_date=today,
        due_date=today + timedelta(days=14),
        line_items=[LineItemDraft(name="Widget", total=Decimal("100"))],
        total_amount=Decimal("100"),
    )
    assert detect_anomalies(extraction, tolerance=0.02) == []
