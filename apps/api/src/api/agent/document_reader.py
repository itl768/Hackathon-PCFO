from __future__ import annotations

import base64
import logging

from openai import AsyncOpenAI

from api.agent.prompts import InvoicePrompts
from api.config import settings

logger = logging.getLogger(__name__)


async def read_document(file_bytes: bytes, content_type: str, filename: str) -> str:
    if content_type in ("text/plain", "text/csv"):
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1")

    if content_type == "application/pdf":
        return await _read_pdf(file_bytes, filename)

    if content_type.startswith("image/"):
        return await _read_image(file_bytes, content_type)

    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return await _read_image(file_bytes, "image/png")


async def _read_pdf(file_bytes: bytes, filename: str) -> str:
    try:
        import fitz

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        if len(text.strip()) > 50:
            return text.strip()

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        doc.close()
        return await _read_image(img_bytes, "image/png")
    except ImportError:
        logger.warning("PyMuPDF not available, falling back to vision for PDF")
        return await _read_image(file_bytes, "application/pdf")


async def _read_image(file_bytes: bytes, content_type: str) -> str:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    media_type = content_type if content_type.startswith("image/") else "image/png"

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": InvoicePrompts.document_reader().content},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    },
                ],
            }
        ],
        max_tokens=4096,
    )
    return response.choices[0].message.content or ""
