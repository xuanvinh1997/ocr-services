from __future__ import annotations

import base64
import binascii
from collections.abc import Iterable

from .backends import LayoutBackend, RecognitionBackend
from .contracts import OCRBlock, OCRDocument, OCRMode
from .settings import Settings


class OCRService:
    def __init__(self, settings: Settings, layout: LayoutBackend, recognition: RecognitionBackend) -> None:
        self.settings, self.layout, self.recognition = settings, layout, recognition

    async def process(self, encoded: str, filename: str, mode: OCRMode) -> OCRDocument:
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError("content_base64 is not valid base64") from error
        if len(content) > self.settings.max_document_bytes:
            raise ValueError(f"document exceeds {self.settings.max_document_bytes} bytes")
        if not content:
            raise ValueError("document is empty")
        if mode is OCRMode.LEGACY:
            raise NotImplementedError("legacy OCR must be configured as an explicit separate backend")

        pages = self._pages(content, filename)
        blocks: list[OCRBlock] = []
        for page, image in enumerate(pages, start=1):
            layout_blocks = await self.layout.analyze(image, page)
            for block in layout_blocks:
                text, confidence = await self.recognition.recognize(image, block.kind)
                blocks.append(block.model_copy(update={"text": text, "confidence": confidence,
                                                       "engine": "PaddleOCR-VL-1.6-0.9B"}))
        blocks.sort(key=lambda item: (item.page, item.order))
        return OCRDocument(
            model_id=self.settings.model_id, model_revision=self.settings.model_revision,
            blocks=blocks, markdown=self._markdown(blocks),
        )

    @staticmethod
    def _pages(content: bytes, filename: str) -> Iterable[bytes]:
        lower = filename.lower()
        if lower.endswith(".pdf"):
            try:
                import pymupdf
                doc = pymupdf.open(stream=content, filetype="pdf")
                if len(doc) == 0:
                    raise ValueError("document has no pages")
                pages: list[bytes] = []
                for page in doc:
                    pix = page.get_pixmap(dpi=150)
                    pages.append(pix.tobytes("png"))
                return pages
            except Exception as error:
                if isinstance(error, ValueError):
                    raise
                raise ValueError(f"failed to parse PDF document: {error}") from error
        if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
            return [content]
        raise ValueError("supported input types are PDF, PNG, JPEG, and WebP")

    @staticmethod
    def _markdown(blocks: list[OCRBlock]) -> str:
        if not blocks:
            return ""
        pages = sorted(set(b.page for b in blocks))
        if len(pages) <= 1:
            return "\n\n".join(block.text for block in blocks)
        page_sections = []
        for p in pages:
            page_blocks = [b.text for b in blocks if b.page == p]
            if page_blocks:
                page_sections.append(f"--- Trang {p} ---\n" + "\n\n".join(page_blocks))
        return "\n\n".join(page_sections)
