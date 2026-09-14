from __future__ import annotations

import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from .backends import LocalPaddleOCRVLRecognition, VLLMRecognition, WholePageLayout
from .contracts import OCRDocument, OCRRequest
from .service import OCRService
from .settings import Settings
from .ui import INDEX_HTML

settings = Settings.from_env()
if settings.recognition_backend == "local":
    recognition = LocalPaddleOCRVLRecognition(settings.model_id, settings.device)
else:
    recognition = VLLMRecognition(settings)

service = OCRService(settings, WholePageLayout(), recognition)
app = FastAPI(title="HPD Vietnamese-English OCR", version="2.0.0")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve web user interface."""
    return HTMLResponse(content=INDEX_HTML)


@app.get("/sample-image")
async def sample_image() -> FileResponse:
    """Provide sample invoice image for instant testing."""
    sample_path = "sample_vn_invoice.png"
    if os.path.exists(sample_path):
        return FileResponse(sample_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Sample image not found")


@app.get("/sample-jpg")
async def sample_jpg() -> FileResponse:
    """Provide sample JPG invoice image for instant testing."""
    sample_path = "sample_vn_invoice.jpg"
    if os.path.exists(sample_path):
        return FileResponse(sample_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Sample JPG image not found")


@app.get("/sample-pdf")
async def sample_pdf() -> FileResponse:
    """Provide sample PDF document for instant testing."""
    sample_path = "sample_vn_document.pdf"
    if os.path.exists(sample_path):
        return FileResponse(sample_path, media_type="application/pdf")
    raise HTTPException(status_code=404, detail="Sample PDF document not found")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "model_id": settings.model_id, "model_revision": settings.model_revision}


@app.post("/v1/ocr", response_model=OCRDocument)
async def ocr(request: OCRRequest) -> OCRDocument:
    try:
        return await service.process(request.content_base64, request.filename, request.mode)
    except (NotImplementedError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def main() -> None:
    import uvicorn
    uvicorn.run("ocr_service.api:app", host="0.0.0.0", port=8000)

