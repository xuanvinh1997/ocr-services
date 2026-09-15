import base64
import io
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from PIL import Image
from ocr_service.backends import VLLMRecognition
from ocr_service.contracts import BoundingBox, ContentType, OCRBlock, OCRMode
from ocr_service.service import OCRService
from ocr_service.settings import Settings

_image_buffer = io.BytesIO()
Image.new("RGB", (2, 2), color="white").save(_image_buffer, format="PNG")
VALID_PNG = _image_buffer.getvalue()


class Layout:
    async def analyze(self, image, page):
        return [OCRBlock(page=page, order=0, kind=ContentType.TEXT,
                         bbox=BoundingBox(x0=0, y0=0, x1=1, y1=1), text="", engine="layout")]


class Recognition:
    async def recognize(self, image, kind):
        return "Tiếng Việt and English", 0.9


class RecordingLayout:
    """Layout fixture whose blocks exercise full-page and normalized crop paths."""

    def __init__(self, blocks):
        self.blocks = blocks
        self.calls = []

    async def analyze(self, image, page):
        self.calls.append((image, page))
        return [block.model_copy(update={"page": page}) for block in self.blocks]


class RecordingRecognition:
    def __init__(self):
        self.calls = []

    async def recognize(self, image, kind):
        self.calls.append((image, kind))
        return f"recognition-{len(self.calls)}", 0.9


class OCRServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        settings = Settings("model", "revision", "http://localhost/v1", "model", 100_000, 1)
        self.service = OCRService(settings, Layout(), Recognition())

    async def test_processes_valid_image_with_provenance(self):
        document = await self.service.process(base64.b64encode(VALID_PNG).decode(), "page.png", OCRMode.VLM)
        self.assertEqual(document.markdown, "Tiếng Việt and English")
        self.assertEqual(document.blocks[0].engine, "PaddleOCR-VL-1.6-0.9B")
        self.assertEqual(document.blocks[0].page, 1)

    async def test_processes_valid_jpg_image(self):
        document = await self.service.process(base64.b64encode(VALID_PNG).decode(), "invoice.jpg", OCRMode.VLM)
        self.assertEqual(document.markdown, "Tiếng Việt and English")
        self.assertEqual(document.blocks[0].page, 1)

    async def test_processes_valid_pdf_document(self):
        import pymupdf
        doc = pymupdf.open()
        doc.new_page()
        doc.new_page()
        pdf_bytes = doc.tobytes()

        settings = Settings("model", "revision", "http://localhost/v1", "model", 100_000, 1)
        service = OCRService(settings, Layout(), Recognition())
        document = await service.process(base64.b64encode(pdf_bytes).decode(), "document.pdf", OCRMode.VLM)
        self.assertEqual(len(document.blocks), 2)
        self.assertEqual(document.blocks[0].page, 1)
        self.assertEqual(document.blocks[1].page, 2)
        self.assertIn("--- Trang 1 ---", document.markdown)
        self.assertIn("--- Trang 2 ---", document.markdown)

    async def test_rejects_invalid_pdf_document(self):
        with self.assertRaisesRegex(ValueError, "failed to parse PDF document"):
            await self.service.process(base64.b64encode(b"not-a-pdf").decode(), "document.pdf", OCRMode.VLM)

    async def test_rejects_invalid_base64(self):
        with self.assertRaisesRegex(ValueError, "valid base64"):
            await self.service.process("***", "page.png", OCRMode.VLM)

    async def test_rejects_oversized_document(self):
        settings = Settings("model", "revision", "http://localhost/v1", "model", 10, 1)
        service = OCRService(settings, Layout(), Recognition())
        with self.assertRaisesRegex(ValueError, "exceeds"):
            await service.process(base64.b64encode(b"01234567890").decode(), "page.png", OCRMode.VLM)

    async def test_legacy_requires_explicit_backend(self):
        with self.assertRaisesRegex(NotImplementedError, "explicit"):
            await self.service.process(base64.b64encode(b"image").decode(), "page.png", OCRMode.LEGACY)

    async def test_recognizes_normalized_layout_crops_not_the_full_page_for_every_block(self):
        # Valid small PNG. A full-page block preserves source bytes, while a
        # partial normalized bounding box must produce a distinct crop.
        image = VALID_PNG
        layout = RecordingLayout([
            OCRBlock(page=1, order=0, kind=ContentType.TEXT,
                     bbox=BoundingBox(x0=0, y0=0, x1=1, y1=1), text="", engine="layout"),
            OCRBlock(page=1, order=1, kind=ContentType.TABLE,
                     bbox=BoundingBox(x0=0, y0=0, x1=0.5, y1=1), text="", engine="layout"),
        ])
        recognition = RecordingRecognition()
        settings = Settings("model", "revision", "http://localhost/v1", "model", 100_000, 1)
        service = OCRService(settings, layout, recognition)

        document = await service.process(base64.b64encode(image).decode(), "page.png", OCRMode.VLM)

        self.assertEqual(len(document.blocks), 2)
        self.assertEqual(recognition.calls[0][0], image)
        self.assertNotEqual(recognition.calls[1][0], image)
        self.assertEqual(recognition.calls[1][1], ContentType.TABLE)

    async def test_rejects_layout_bounding_box_outside_normalized_page(self):
        layout = RecordingLayout([
            OCRBlock(page=1, order=0, kind=ContentType.TEXT,
                     bbox=BoundingBox(x0=0, y0=0, x1=1.01, y1=1), text="", engine="layout"),
        ])
        recognition = RecordingRecognition()
        settings = Settings("model", "revision", "http://localhost/v1", "model", 100_000, 1)
        service = OCRService(settings, layout, recognition)

        with self.assertRaisesRegex(ValueError, "bounding box"):
            await service.process(base64.b64encode(VALID_PNG).decode(), "page.png", OCRMode.VLM)
        self.assertEqual(recognition.calls, [])

    async def test_hybrid_uses_native_pdf_text_without_layout_or_vlm(self):
        import pymupdf

        pdf = pymupdf.open()
        page = pdf.new_page()
        page.insert_text((72, 72), "Bilingual native PDF text")
        layout = RecordingLayout([])
        recognition = RecordingRecognition()
        settings = Settings("model", "revision", "http://localhost/v1", "model", 100_000, 1)
        service = OCRService(settings, layout, recognition)

        document = await service.process(base64.b64encode(pdf.tobytes()).decode(), "native.pdf", OCRMode.HYBRID)

        self.assertEqual(len(layout.calls), 0)
        self.assertEqual(recognition.calls, [])
        self.assertEqual(len(document.blocks), 1)
        self.assertEqual(document.blocks[0].engine, "PDF-native-text")
        self.assertEqual(document.blocks[0].confidence, 1.0)
        self.assertIn("Bilingual native PDF text", document.markdown)

    async def test_enforces_pdf_page_count_limit_before_ocr(self):
        import pymupdf

        pdf = pymupdf.open()
        pdf.new_page()
        pdf.new_page()
        settings = Settings("model", "revision", "http://localhost/v1", "model", 100_000, 1, max_pages=1)
        layout = RecordingLayout([])
        recognition = RecordingRecognition()
        service = OCRService(settings, layout, recognition)

        with self.assertRaisesRegex(ValueError, "page"):
            await service.process(base64.b64encode(pdf.tobytes()).decode(), "document.pdf", OCRMode.VLM)
        self.assertEqual(layout.calls, [])
        self.assertEqual(recognition.calls, [])

    async def test_enforces_rendered_page_pixel_limit_before_ocr(self):
        import pymupdf

        pdf = pymupdf.open()
        pdf.new_page(width=72, height=72)
        settings = Settings("model", "revision", "http://localhost/v1", "model", 100_000, 1,
                            max_page_pixels=1)
        layout = RecordingLayout([])
        recognition = RecordingRecognition()
        service = OCRService(settings, layout, recognition)

        with self.assertRaisesRegex(ValueError, "pixel"):
            await service.process(base64.b64encode(pdf.tobytes()).decode(), "document.pdf", OCRMode.VLM)
        self.assertEqual(layout.calls, [])
        self.assertEqual(recognition.calls, [])

    async def test_enforces_image_pixel_limit_before_ocr(self):
        layout = RecordingLayout([])
        recognition = RecordingRecognition()
        settings = Settings("model", "revision", "http://localhost/v1", "model", 100_000, 1,
                            max_page_pixels=1)
        service = OCRService(settings, layout, recognition)

        with self.assertRaisesRegex(ValueError, "image exceeds"):
            await service.process(base64.b64encode(VALID_PNG).decode(), "document.png", OCRMode.VLM)
        self.assertEqual(layout.calls, [])
        self.assertEqual(recognition.calls, [])


class VLLMRecognitionTests(unittest.IsolatedAsyncioTestCase):
    class Response:
        def __init__(self, status_code, content="recognized"):
            self.status_code = status_code
            self._content = content
            self.text = "upstream error"

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("unexpected response")

        def json(self):
            return {"choices": [{"message": {"content": self._content}}]}

    class Client:
        is_closed = False

        def __init__(self, responses):
            self.responses = iter(responses)
            self.requests = []

        async def post(self, url, json):
            self.requests.append((url, json))
            return next(self.responses)

    def _settings(self, **overrides):
        values = {"vllm_max_tokens": 321, "vllm_temperature": 0.2, "vllm_retries": 1}
        values.update(overrides)
        return Settings("model", "revision", "http://localhost/v1", "served-model", 100_000, 1, **values)

    async def test_vllm_recognition_reuses_client_and_sends_bounded_payload(self):
        recognition = VLLMRecognition(self._settings())
        client = self.Client([self.Response(200), self.Response(200)])
        recognition._client = client

        first, _ = await recognition.recognize(b"\xff\xd8\xffjpeg", ContentType.TEXT)
        second, _ = await recognition.recognize(b"png", ContentType.TABLE)

        self.assertEqual((first, second), ("recognized", "recognized"))
        self.assertEqual(len(client.requests), 2)
        first_payload = client.requests[0][1]
        self.assertEqual(first_payload["model"], "served-model")
        self.assertEqual(first_payload["max_tokens"], 321)
        self.assertEqual(first_payload["temperature"], 0.2)
        self.assertTrue(first_payload["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;"))

    async def test_vllm_retries_transient_overload_then_returns_result(self):
        recognition = VLLMRecognition(self._settings(vllm_retries=1))
        recognition._client = self.Client([self.Response(503), self.Response(200, "recovered")])

        with patch("ocr_service.backends.asyncio.sleep", new_callable=AsyncMock) as sleep:
            text, confidence = await recognition.recognize(b"png", ContentType.TEXT)

        self.assertEqual((text, confidence), ("recovered", None))
        sleep.assert_awaited_once_with(0.1)

    async def test_vllm_wraps_non_retryable_http_errors(self):
        class BadRequestClient:
            is_closed = False

            async def post(self, url, json):
                return httpx.Response(400, text="bad request", request=httpx.Request("POST", url))

        recognition = VLLMRecognition(self._settings())
        recognition._client = BadRequestClient()

        with self.assertRaisesRegex(RuntimeError, "HTTP 400"):
            await recognition.recognize(b"png", ContentType.TEXT)


class APITests(unittest.TestCase):
    def test_index_and_healthz(self):
        from fastapi.testclient import TestClient
        from ocr_service.api import app

        client = TestClient(app)
        res_health = client.get("/healthz")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "ok")

        res_ui = client.get("/")
        self.assertEqual(res_ui.status_code, 200)
        self.assertIn("HPD OCR Studio", res_ui.text)
        self.assertIn(".pdf", res_ui.text)
        self.assertIn(".jpg", res_ui.text)
        self.assertIn("pdf-preview", res_ui.text)
        self.assertIn("btn-sample-jpg", res_ui.text)
        self.assertIn("btn-sample-pdf", res_ui.text)

    def test_sample_endpoints(self):
        from fastapi.testclient import TestClient
        from ocr_service.api import app

        client = TestClient(app)
        res_img = client.get("/sample-image")
        self.assertEqual(res_img.status_code, 200)

        res_jpg = client.get("/sample-jpg")
        self.assertEqual(res_jpg.status_code, 200)
        self.assertEqual(res_jpg.headers["content-type"], "image/jpeg")

        res_pdf = client.get("/sample-pdf")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.headers["content-type"], "application/pdf")

    def test_ocr_api_with_jpg_and_pdf(self):
        from unittest.mock import AsyncMock, patch
        from fastapi.testclient import TestClient
        from ocr_service.api import app, service

        client = TestClient(app)

        with patch.object(service.recognition, "recognize", new_callable=AsyncMock) as mock_rec:
            mock_rec.return_value = ("Nội dung trích xuất", 0.98)

            # Test JPG OCR via API
            res_jpg = client.post("/v1/ocr", json={
                "content_base64": base64.b64encode(VALID_PNG).decode(),
                "filename": "invoice.jpg",
                "mode": "vlm"
            })
            self.assertEqual(res_jpg.status_code, 200)
            self.assertIn("Nội dung trích xuất", res_jpg.json()["markdown"])

            # Test PDF OCR via API
            import pymupdf
            doc = pymupdf.open()
            doc.new_page()
            pdf_bytes = doc.tobytes()

            res_pdf = client.post("/v1/ocr", json={
                "content_base64": base64.b64encode(pdf_bytes).decode(),
                "filename": "invoice.pdf",
                "mode": "vlm"
            })
            self.assertEqual(res_pdf.status_code, 200)
            self.assertIn("Nội dung trích xuất", res_pdf.json()["markdown"])

