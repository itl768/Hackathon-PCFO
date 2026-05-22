from __future__ import annotations

from api.invoicing.application.ports import InvoiceRepository
from api.invoicing.domain import Invoice, InvoiceId


class GetInvoice:
    def __init__(self, *, invoice_repository: InvoiceRepository) -> None:
        self._invoice_repository = invoice_repository

    async def execute(self, invoice_id: InvoiceId) -> Invoice:
        return await self._invoice_repository.get(invoice_id)

    async def list_recent(self, *, limit: int = 50, offset: int = 0) -> list[Invoice]:
        return await self._invoice_repository.list_recent(limit=limit, offset=offset)
