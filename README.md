# Vietnamese-English OCR service V2

Production-oriented document OCR orchestration using `PaddlePaddle/PaddleOCR-VL-1.6`
served by a local vLLM-compatible endpoint. In `hybrid` mode, PDF pages with usable
native text bypass OCR; remaining pages are rendered one at a time, segmented by a
layout backend, recognized crop-by-crop, and returned with Markdown and provenance.
The built-in whole-page layout backend is a safe fallback; configure a real layout
adapter before relying on region-level document semantics in production.

## Quick start

```powershell
python -m pip install -e ".[test]"
python -m pytest
Copy-Item .env.example .env
ocr-api
```

For a real worker, install the Paddle extras in its own compatible Python/CUDA
environment and configure `VLLM_BASE_URL`. The API process deliberately does not
install, download, or upgrade models at runtime.

## Production limits

`MAX_DOCUMENT_BYTES`, `MAX_DOCUMENT_PAGES`, `MAX_PAGE_PIXELS`, and
`MAX_TOTAL_RENDERED_PIXELS` protect the service from oversized uploads and expensive
PDF rendering. vLLM output, connection-pool size, and retry behavior are configured
through the `VLLM_*` variables in `.env.example`. Local inference is serialized per
process to protect GPU memory; scale it with separate worker processes only after
sizing GPU memory for one model copy per process.

## Endpoints & UI

* `GET /` - **HPD OCR Studio Web UI**: Giao diện trực quan trên trình duyệt (kéo/thả ảnh JPG/PNG/WebP và tài liệu PDF đơn/đa trang, xem trước với PDF.js canvas, các nút nạp mẫu JPG/PDF/PNG nhanh, trích xuất text/JSON thời gian thực, sao chép & tải kết quả).
* `GET /sample-image` - Cung cấp ảnh hóa đơn mẫu PNG.
* `GET /sample-jpg` - Cung cấp ảnh hóa đơn mẫu JPG.
* `GET /sample-pdf` - Cung cấp tài liệu mẫu PDF 2 trang.
* `GET /docs` - Swagger API Documentation tương tác.
* `GET /healthz` - Trạng thái server và model contract.
* `POST /v1/ocr` - REST API xử lý tài liệu (PDF, PNG, JPG, WebP) dạng base64.
* `scripts/run_inference.py` - CLI chạy trực tiếp inference bằng GPU trên một ảnh.

See `docs/FINETUNING.md` for data contracts and `docs/OPERATIONS.md` for the
release-lock procedure.
