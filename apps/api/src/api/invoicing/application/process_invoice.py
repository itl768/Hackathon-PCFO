from __future__ import annotations

from dataclasses import dataclass

from api.invoicing.application.ports import (
    DocumentStore,
    EventPublisher,
    InvoiceRepository,
    PipelineRunner,
)
from api.invoicing.domain import Invoice, InvoiceReceived


@dataclass(frozen=True)
class UploadedDocument:
    original_filename: str
    mime_type: str
    content: bytes


class UnsupportedFileType(Exception):
    def __init__(self, mime_type: str) -> None:
        super().__init__(f"Unsupported file type: {mime_type}")
        self.mime_type = mime_type


class FileTooLarge(Exception):
    def __init__(self, *, byte_size: int, max_bytes: int) -> None:
        super().__init__(f"File too large: {byte_size} bytes (max {max_bytes})")
        self.byte_size = byte_size
        self.max_bytes = max_bytes


class ProcessInvoice:
    def __init__(
        self,
        *,
        document_store: DocumentStore,
        invoice_repository: InvoiceRepository,
        event_publisher: EventPublisher,
        pipeline_runner: PipelineRunner,
        allowed_mime_types: list[str],
        max_upload_bytes: int,
    ) -> None:
        self._document_store = document_store
        self._invoice_repository = invoice_repository
        self._event_publisher = event_publisher
        self._pipeline_runner = pipeline_runner
        self._allowed_mime_types = set(allowed_mime_types)
        self._max_upload_bytes = max_upload_bytes

    async def execute(
        self,
        *,
        upload: UploadedDocument,
        force_duplicate: bool = False,
    ) -> Invoice:
        self._validate(upload)

        stored = await self._document_store.store(
            original_filename=upload.original_filename,
            mime_type=upload.mime_type,
            content=upload.content,
        )

        invoice = Invoice.newly_received(
            original_filename=upload.original_filename,
            mime_type=upload.mime_type,
            sha256=stored.sha256,
            document_uri=stored.document_uri,
        )
        await self._invoice_repository.save(invoice)

        await self._event_publisher.publish(
            InvoiceReceived(
                invoice_id=invoice.id,
                original_filename=upload.original_filename,
                mime_type=upload.mime_type,
            )
        )

        await self._pipeline_runner.run(
            invoice_id=invoice.id,
            force_duplicate=force_duplicate,
        )

        return invoice

    def _validate(self, upload: UploadedDocument) -> None:
        if upload.mime_type not in self._allowed_mime_types:
            raise UnsupportedFileType(upload.mime_type)
        byte_size = len(upload.content)
        if byte_size > self._max_upload_bytes:
            raise FileTooLarge(byte_size=byte_size, max_bytes=self._max_upload_bytes)
