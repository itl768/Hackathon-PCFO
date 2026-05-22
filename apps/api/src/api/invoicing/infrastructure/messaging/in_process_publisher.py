from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator

from api.invoicing.application.ports import EventPublisher
from api.invoicing.domain import DomainEvent, InvoiceId


class InProcessEventPublisher(EventPublisher):
    def __init__(self, *, buffer_limit: int = 500) -> None:
        self._subscribers: dict[InvoiceId, list[asyncio.Queue[DomainEvent | None]]] = defaultdict(
            list
        )
        self._buffer: dict[InvoiceId, list[DomainEvent]] = defaultdict(list)
        self._finalized: set[InvoiceId] = set()
        self._buffer_limit = buffer_limit

    async def publish(self, event: DomainEvent) -> None:
        buffer = self._buffer[event.invoice_id]
        buffer.append(event)
        if len(buffer) > self._buffer_limit:
            del buffer[0 : len(buffer) - self._buffer_limit]
        for queue in list(self._subscribers.get(event.invoice_id, ())):
            await queue.put(event)

    def subscribe(self, invoice_id: InvoiceId) -> AsyncIterator[DomainEvent]:
        queue: asyncio.Queue[DomainEvent | None] = asyncio.Queue()
        for buffered in self._buffer.get(invoice_id, ()):
            queue.put_nowait(buffered)
        if invoice_id in self._finalized:
            queue.put_nowait(None)
        else:
            self._subscribers[invoice_id].append(queue)
        return self._iterate(invoice_id, queue)

    async def _iterate(
        self,
        invoice_id: InvoiceId,
        queue: asyncio.Queue[DomainEvent | None],
    ) -> AsyncIterator[DomainEvent]:
        try:
            while True:
                event = await queue.get()
                if event is None:
                    return
                yield event
        finally:
            self._detach(invoice_id, queue)

    async def close(self, invoice_id: InvoiceId) -> None:
        self._finalized.add(invoice_id)
        for queue in list(self._subscribers.get(invoice_id, ())):
            await queue.put(None)

    def _detach(
        self,
        invoice_id: InvoiceId,
        queue: asyncio.Queue[DomainEvent | None],
    ) -> None:
        queues = self._subscribers.get(invoice_id)
        if queues is not None and queue in queues:
            queues.remove(queue)
            if not queues:
                self._subscribers.pop(invoice_id, None)
