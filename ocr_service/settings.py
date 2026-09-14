from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    model_id: str
    model_revision: str
    vllm_base_url: str
    vllm_model_name: str
    max_document_bytes: int
    request_timeout_seconds: float
    recognition_backend: str = "vllm"
    device: str = "cuda"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model_id=getenv("OCR_MODEL_ID", "PaddlePaddle/PaddleOCR-VL-1.6"),
            model_revision=getenv("OCR_MODEL_REVISION", "unlocked-development"),
            vllm_base_url=getenv("VLLM_BASE_URL", "http://127.0.0.1:8001/v1").rstrip("/"),
            vllm_model_name=getenv("VLLM_MODEL_NAME", "PaddleOCR-VL-1.6-0.9B"),
            max_document_bytes=int(getenv("MAX_DOCUMENT_BYTES", "26214400")),
            request_timeout_seconds=float(getenv("REQUEST_TIMEOUT_SECONDS", "120")),
            recognition_backend=getenv("RECOGNITION_BACKEND", "vllm"),
            device=getenv("DEVICE", "cuda"),
        )

