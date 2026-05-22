from __future__ import annotations

import asyncio
from io import BytesIO

import pypdfium2 as pdfium

from api.invoicing.domain import ExtractionFailed


async def rasterise_pdf(
    content: bytes,
    *,
    scale: float,
    max_pages: int,
) -> list[bytes]:
    return await asyncio.to_thread(_rasterise_sync, content, scale, max_pages)


def _rasterise_sync(content: bytes, scale: float, max_pages: int) -> list[bytes]:
    try:
        pdf = pdfium.PdfDocument(content)
    except Exception as exc:
        raise ExtractionFailed(f"Could not open PDF: {exc}") from exc

    try:
        total_pages = len(pdf)
        if total_pages == 0:
            raise ExtractionFailed("PDF has no pages")

        pages_to_process = min(total_pages, max_pages)
        images: list[bytes] = []

        for index in range(pages_to_process):
            page = pdf[index]
            try:
                pil_image = page.render(scale=scale).to_pil()
                buffer = BytesIO()
                pil_image.save(buffer, format="PNG")
                images.append(buffer.getvalue())
            finally:
                page.close()

        return images
    finally:
        pdf.close()
