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
    vllm_max_tokens: int = 1024
    vllm_temperature: float = 0.0
    vllm_max_connections: int = 20
    vllm_retries: int = 2
    local_max_new_tokens: int = 1024
    local_torch_dtype: str = "auto"
    max_pages: int = 100
    max_page_pixels: int = 40_000_000
    max_total_rendered_pixels: int = 200_000_000

    def __post_init__(self) -> None:
        positive = {
            "max_document_bytes": self.max_document_bytes,
            "request_timeout_seconds": self.request_timeout_seconds,
            "vllm_max_tokens": self.vllm_max_tokens,
            "vllm_max_connections": self.vllm_max_connections,
            "local_max_new_tokens": self.local_max_new_tokens,
            "max_pages": self.max_pages,
            "max_page_pixels": self.max_page_pixels,
            "max_total_rendered_pixels": self.max_total_rendered_pixels,
        }
        invalid = [name for name, value in positive.items() if value <= 0]
        if invalid:
            raise ValueError(f"settings must be positive: {', '.join(invalid)}")
        if self.vllm_retries < 0:
            raise ValueError("vllm_retries cannot be negative")
        if self.vllm_temperature < 0:
            raise ValueError("vllm_temperature cannot be negative")
        if self.recognition_backend not in {"vllm", "local"}:
            raise ValueError("RECOGNITION_BACKEND must be vllm or local")

    @classmethod
    def from_env(cls) -> "Settings":
        # Keep the documented `Copy-Item .env .env` setup usable outside Uvicorn.
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            # Environment variables remain fully supported for container deployments.
            pass
        return cls(
            model_id=getenv("OCR_MODEL_ID", "PaddlePaddle/PaddleOCR-VL-1.6"),
            model_revision=getenv("OCR_MODEL_REVISION", "unlocked-development"),
            vllm_base_url=getenv("VLLM_BASE_URL", "http://127.0.0.1:8001/v1").rstrip("/"),
            vllm_model_name=getenv("VLLM_MODEL_NAME", "PaddleOCR-VL-1.6-0.9B"),
            max_document_bytes=int(getenv("MAX_DOCUMENT_BYTES", "26214400")),
            request_timeout_seconds=float(getenv("REQUEST_TIMEOUT_SECONDS", "120")),
            recognition_backend=getenv("RECOGNITION_BACKEND", "vllm"),
            device=getenv("DEVICE", "cuda"),
            vllm_max_tokens=int(getenv("VLLM_MAX_TOKENS", "1024")),
            vllm_temperature=float(getenv("VLLM_TEMPERATURE", "0")),
            vllm_max_connections=int(getenv("VLLM_MAX_CONNECTIONS", "20")),
            vllm_retries=int(getenv("VLLM_RETRIES", "2")),
            local_max_new_tokens=int(getenv("LOCAL_MAX_NEW_TOKENS", "1024")),
            local_torch_dtype=getenv("LOCAL_TORCH_DTYPE", "auto"),
            max_pages=int(getenv("MAX_DOCUMENT_PAGES", "100")),
            max_page_pixels=int(getenv("MAX_PAGE_PIXELS", "40000000")),
            max_total_rendered_pixels=int(getenv("MAX_TOTAL_RENDERED_PIXELS", "200000000")),
        )

