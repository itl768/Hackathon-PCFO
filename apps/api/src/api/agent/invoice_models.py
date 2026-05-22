from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str = ""
    quantity: float = 1.0
    unit_price: float = 0.0
    net_amount: float = 0.0
    vat_amount: float = 0.0
    line_total: float = 0.0


class ExtractedInvoice(BaseModel):
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: float | None = None
    vat_total: float | None = None
    total_amount: float | None = None
    currency: str = "USD"
    payment_terms: str | None = None


class DuplicationResult(BaseModel):
    is_duplicate: bool = False
    similarity_score: float = 0.0
    matched_invoice_id: int | None = None
    matched_invoice_number: str | None = None
    method: str = "vector"


class ValidationRule(BaseModel):
    rule_name: str
    passed: bool
    message: str


class AnomalyFlag(BaseModel):
    flag_type: str
    severity: str = "medium"
    description: str


class ValidationResult(BaseModel):
    rules: list[ValidationRule] = Field(default_factory=list)
    all_passed: bool = True
    failed_count: int = 0


class AnomalyResult(BaseModel):
    flags: list[AnomalyFlag] = Field(default_factory=list)
    risk_score: int = 0
    risk_level: str = "low"


class AgentLogEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    agent_name: str
    message: str
    status: str = "info"
    data: dict | None = None


class ApprovalStatus(str, Enum):
    AUTO_APPROVE = "Auto-Approve"
    MANUAL_REVIEW = "Manual Review Required"
    REJECT = "Reject"
    DUPLICATE_REJECT = "Duplicate - Reject"


class ProcessingReport(BaseModel):
    summary: str = ""
    agent_outputs: dict = Field(default_factory=dict)
    decision: str = ""
    recommendation: str = ""
    confidence: str = ""
    risk_score: int = 0
    next_steps: list[str] = Field(default_factory=list)
    extracted_invoice: ExtractedInvoice | None = None
    dedup_vector: DuplicationResult | None = None
    dedup_exact: DuplicationResult | None = None
    validation: ValidationResult | None = None
    anomalies: AnomalyResult | None = None
