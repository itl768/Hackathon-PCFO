from __future__ import annotations

from dataclasses import dataclass

from api.invoicing.domain.invoice import InvoiceId


@dataclass(frozen=True)
class DuplicateMatch:
    matched_invoice_id: InvoiceId
    match_keys: dict[str, str]
