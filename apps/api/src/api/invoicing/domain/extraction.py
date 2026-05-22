from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LineItemDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    quantity: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    total: Decimal = Decimal("0")


class FieldConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_path: str
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_number: str | None = None
    vendor_name: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    line_items: list[LineItemDraft] = Field(default_factory=list)
    total_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    currency: str = "USD"
    field_confidences: list[FieldConfidence] = Field(default_factory=list)

    @classmethod
    def empty(cls) -> ExtractionResult:
        return cls()

    def filled_field_count(self) -> int:
        scalar_fields = (
            self.invoice_number,
            self.vendor_name,
            self.invoice_date,
            self.due_date,
            self.total_amount,
            self.tax_amount,
        )
        filled = sum(1 for value in scalar_fields if value is not None and value != "")
        if self.line_items:
            filled += 1
        return filled

    def has_natural_key(self) -> bool:
        return (
            bool(self.invoice_number and self.invoice_number.strip())
            and bool(self.vendor_name and self.vendor_name.strip())
            and self.invoice_date is not None
        )


class ExtractionFailed(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
