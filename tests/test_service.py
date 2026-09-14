import base64
import unittest

from ocr_service.contracts import BoundingBox, ContentType, OCRBlock, OCRMode
from ocr_service.service import OCRService
from ocr_service.settings import Settings


class Layout:
    async def analyze(self, image, page):
        return [OCRBlock(page=page, order=0, kind=ContentType.TEXT,
                         bbox=BoundingBox(x0=0, y0=0, x1=1, y1=1), text="", engine="layout")]


class Recognition:
    async def recognize(self, image, kind):
        return "Tiếng Việt and English", 0.9


class OCRServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        settings = Settings("model", "revision", "http://localhost/v1", "model", 10, 1)
        self.service = OCRService(settings, Layout(), Recognition())

    async def test_processes_valid_image_with_provenance(self):
        document = await self.service.process(base64.b64encode(b"image").decode(), "page.png", OCRMode.VLM)
        self.assertEqual(document.markdown, "Tiếng Việt and English")
        self.assertEqual(document.blocks[0].engine, "PaddleOCR-VL-1.6-0.9B")
        self.assertEqual(document.blocks[0].page, 1)

    async def test_processes_valid_jpg_image(self):
        document = await self.service.process(base64.b64encode(b"image").decode(), "invoice.jpg", OCRMode.VLM)
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
        with self.assertRaisesRegex(ValueError, "exceeds"):
            await self.service.process(base64.b64encode(b"01234567890").decode(), "page.png", OCRMode.VLM)

    async def test_legacy_requires_explicit_backend(self):
        with self.assertRaisesRegex(NotImplementedError, "explicit"):
            await self.service.process(base64.b64encode(b"image").decode(), "page.png", OCRMode.LEGACY)


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
                "content_base64": base64.b64encode(b"fake_jpg_bytes").decode(),
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

