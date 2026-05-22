from __future__ import annotations

import hashlib
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import aiofiles

from api.invoicing.application.ports import DocumentStore, StoredDocument

_MIME_TO_EXTENSION = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}

_SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class LocalDocumentStore(DocumentStore):
    def __init__(self, root_path: str) -> None:
        self._root = Path(root_path)
        self._root.mkdir(parents=True, exist_ok=True)

    async def store(
        self,
        *,
        original_filename: str,
        mime_type: str,
        content: bytes,
    ) -> StoredDocument:
        sha256 = hashlib.sha256(content).hexdigest()
        now = datetime.now(UTC)
        relative_dir = Path(f"{now.year:04d}") / f"{now.month:02d}" / f"{now.day:02d}"
        absolute_dir = self._root / relative_dir
        absolute_dir.mkdir(parents=True, exist_ok=True)

        extension = _MIME_TO_EXTENSION.get(mime_type) or Path(original_filename).suffix or ".bin"
        safe_stem = _SAFE_NAME_PATTERN.sub("_", Path(original_filename).stem)[:80] or "invoice"
        filename = f"{sha256[:16]}__{safe_stem}{extension}"
        absolute_path = absolute_dir / filename

        async with aiofiles.open(absolute_path, "wb") as fh:
            await fh.write(content)

        document_uri = str((relative_dir / filename).as_posix())
        return StoredDocument(
            document_uri=document_uri,
            sha256=sha256,
            byte_size=len(content),
        )

    async def read(self, document_uri: str) -> bytes:
        path = self._resolve(document_uri)
        async with aiofiles.open(path, "rb") as fh:
            return await fh.read()

    async def stream(self, document_uri: str) -> AsyncIterator[bytes]:
        path = self._resolve(document_uri)
        async with aiofiles.open(path, "rb") as fh:
            while True:
                chunk = await fh.read(64 * 1024)
                if not chunk:
                    return
                yield chunk

    def _resolve(self, document_uri: str) -> Path:
        candidate = (self._root / document_uri).resolve()
        root_resolved = self._root.resolve()
        if root_resolved not in candidate.parents and candidate != root_resolved:
            raise DocumentNotFound(document_uri)
        if not candidate.exists():
            raise DocumentNotFound(document_uri)
        return candidate


class DocumentNotFound(Exception):
    def __init__(self, document_uri: str) -> None:
        super().__init__(f"Document not found: {document_uri}")
        self.document_uri = document_uri
