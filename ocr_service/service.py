from __future__ import annotations

import base64
import binascii
import io
import math
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass

from .backends import LayoutBackend, RecognitionBackend
from .contracts import OCRBlock, OCRDocument, OCRMode
from .settings import Settings


@dataclass(frozen=True)
class _Page:
    number: int
    image: bytes | None
    native_text: str | None


class OCRService:
    def __init__(self, settings: Settings, layout: LayoutBackend, recognition: RecognitionBackend) -> None:
        self.settings, self.layout, self.recognition = settings, layout, recognition

    async def process(self, encoded: str, filename: str, mode: OCRMode) -> OCRDocument:
        # Avoid allocating a decoded upload that is necessarily over the limit.
        max_encoded_bytes = math.ceil(self.settings.max_document_bytes / 3) * 4
        if len(encoded) > max_encoded_bytes:
            raise ValueError(f"document exceeds {self.settings.max_document_bytes} bytes")
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

        blocks: list[OCRBlock] = []
        for page in self._pages(content, filename, mode):
            if mode is OCRMode.HYBRID and page.native_text:
                blocks.append(OCRBlock(
                    page=page.number, order=0, kind="text",
                    bbox={"x0": 0, "y0": 0, "x1": 1, "y1": 1},
                    text=page.native_text, confidence=1.0, engine="PDF-native-text",
                ))
                continue
            if page.image is None:
                raise ValueError(f"page {page.number} has no raster image")
            layout_blocks = await self.layout.analyze(page.image, page.number)
            for block in layout_blocks:
                text, confidence = await self.recognition.recognize(self._crop(page.image, block), block.kind)
                blocks.append(block.model_copy(update={
                    "text": text, "confidence": confidence, "engine": "PaddleOCR-VL-1.6-0.9B",
                }))
        blocks.sort(key=lambda item: (item.page, item.order))
        return OCRDocument(
            model_id=self.settings.model_id,
            model_revision=self.settings.model_revision,
            blocks=blocks,
            markdown=self._markdown(blocks),
        )

    def _pages(self, content: bytes, filename: str, mode: OCRMode) -> Iterator[_Page]:
        lower = filename.lower()
        if lower.endswith(".pdf"):
            yield from self._pdf_pages(content, mode)
            return
        if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
            self._validate_image(content)
            yield _Page(number=1, image=content, native_text=None)
            return
        raise ValueError("supported input types are PDF, PNG, JPEG, and WebP")

    def _validate_image(self, content: bytes) -> None:
        """Decode-check direct uploads and apply the same per-page pixel ceiling."""
        try:
            from PIL import Image
            with Image.open(io.BytesIO(content)) as source:
                pixels = source.width * source.height
                source.verify()
        except Exception as error:
            raise ValueError(f"failed to parse image document: {error}") from error
        if pixels > self.settings.max_page_pixels:
            raise ValueError(f"image exceeds {self.settings.max_page_pixels} pixels")

    def _pdf_pages(self, content: bytes, mode: OCRMode) -> Iterator[_Page]:
        try:
            import pymupdf
            doc = pymupdf.open(stream=content, filetype="pdf")
        except Exception as error:
            raise ValueError(f"failed to parse PDF document: {error}") from error
        try:
            page_count = len(doc)
            if page_count == 0:
                raise ValueError("document has no pages")
            if page_count > self.settings.max_pages:
                raise ValueError(f"document exceeds {self.settings.max_pages} pages")

            total_pixels = 0
            for number, pdf_page in enumerate(doc, start=1):
                native_text = pdf_page.get_text("text").strip() if mode is OCRMode.HYBRID else None
                if native_text:
                    # Native pages do not need a potentially large raster buffer.
                    yield _Page(number=number, image=None, native_text=native_text)
                    continue
                pix = pdf_page.get_pixmap(dpi=150)
                pixels = pix.width * pix.height
                if pixels > self.settings.max_page_pixels:
                    raise ValueError(f"page {number} exceeds {self.settings.max_page_pixels} pixels")
                total_pixels += pixels
                if total_pixels > self.settings.max_total_rendered_pixels:
                    raise ValueError(
                        f"rendered document exceeds {self.settings.max_total_rendered_pixels} pixels"
                    )
                yield _Page(number=number, image=pix.tobytes("png"), native_text=None)
        except ValueError:
            raise
        except Exception as error:
            raise ValueError(f"failed to parse PDF document: {error}") from error
        finally:
            doc.close()

    @staticmethod
    def _crop(image: bytes, block: OCRBlock) -> bytes:
        """Crop a layout block whose coordinates are normalized to [0, 1]."""
        bbox = block.bbox
        if (bbox.x0, bbox.y0, bbox.x1, bbox.y1) == (0, 0, 1, 1):
            return image
        if not (0 <= bbox.x0 < bbox.x1 <= 1 and 0 <= bbox.y0 < bbox.y1 <= 1):
            raise ValueError("layout bounding box must be normalized to the [0, 1] range")
        try:
            from PIL import Image
            with Image.open(io.BytesIO(image)) as source:
                width, height = source.size
                left, top = math.floor(bbox.x0 * width), math.floor(bbox.y0 * height)
                right, bottom = math.ceil(bbox.x1 * width), math.ceil(bbox.y1 * height)
                if right <= left or bottom <= top:
                    raise ValueError("layout bounding box is empty after pixel conversion")
                output = io.BytesIO()
                source.crop((left, top, right, bottom)).save(output, format="PNG")
                return output.getvalue()
        except ValueError:
            raise
        except Exception as error:
            raise ValueError(f"failed to crop layout block: {error}") from error

    @staticmethod
    def _markdown(blocks: list[OCRBlock]) -> str:
        if not blocks:
            return ""
        by_page: dict[int, list[str]] = defaultdict(list)
        for block in blocks:
            if block.text:
                by_page[block.page].append(block.text)
        if len(by_page) <= 1:
            return "\n\n".join(block.text for block in blocks)
        return "\n\n".join(
            f"--- Trang {page} ---\n" + "\n\n".join(page_blocks)
            for page, page_blocks in sorted(by_page.items())
        )
