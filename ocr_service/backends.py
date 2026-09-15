from __future__ import annotations

import base64
import asyncio
import io
import threading
from typing import Protocol
import httpx

from .contracts import BoundingBox, ContentType, OCRBlock
from .settings import Settings


class LayoutBackend(Protocol):
    async def analyze(self, image: bytes, page: int) -> list[OCRBlock]: ...


class RecognitionBackend(Protocol):
    async def recognize(self, image: bytes, kind: ContentType) -> tuple[str, float | None]: ...


class WholePageLayout:
    """Safe development fallback; production uses a PP-DocLayoutV3 adapter."""

    async def analyze(self, image: bytes, page: int) -> list[OCRBlock]:
        return [OCRBlock(
            page=page, order=0, kind=ContentType.TEXT,
            bbox=BoundingBox(x0=0, y0=0, x1=1, y1=1), text="", engine="PP-DocLayoutV3",
        )]


class VLLMRecognition:
    TASK_PROMPTS = {
        ContentType.TEXT: "OCR:",
        ContentType.TABLE: "Table Recognition:",
        ContentType.FORMULA: "Formula Recognition:",
        ContentType.CHART: "Chart Recognition:",
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if settings.vllm_max_tokens < 1:
            raise ValueError("VLLM_MAX_TOKENS must be positive")
        if settings.vllm_max_connections < 1:
            raise ValueError("VLLM_MAX_CONNECTIONS must be positive")
        if settings.vllm_retries < 0:
            raise ValueError("VLLM_RETRIES cannot be negative")
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        """Create the connection pool in the application's active event loop."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.request_timeout_seconds),
                limits=httpx.Limits(
                    max_connections=self.settings.vllm_max_connections,
                    max_keepalive_connections=self.settings.vllm_max_connections,
                ),
            )

    async def close(self) -> None:
        """Release pooled HTTP connections during application shutdown."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def recognize(self, image: bytes, kind: ContentType) -> tuple[str, float | None]:
        await self.start()
        assert self._client is not None
        media_type = "image/png"
        if image.startswith(b"\xff\xd8\xff"):
            media_type = "image/jpeg"
        elif image.startswith(b"RIFF") and b"WEBP" in image[:12]:
            media_type = "image/webp"
        image_url = f"data:{media_type};base64," + base64.b64encode(image).decode("ascii")
        payload = {
            "model": self.settings.vllm_model_name,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": self.TASK_PROMPTS[kind]},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]}],
            "temperature": self.settings.vllm_temperature,
            "max_tokens": self.settings.vllm_max_tokens,
        }
        response: httpx.Response | None = None
        for attempt in range(self.settings.vllm_retries + 1):
            try:
                response = await self._client.post(
                    f"{self.settings.vllm_base_url}/chat/completions", json=payload
                )
                # Retry overloaded and temporarily unavailable model servers.
                if response.status_code not in {429, 502, 503, 504}:
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        detail = response.text[:500]
                        raise RuntimeError(
                            f"vLLM returned HTTP {response.status_code}: {detail}"
                        ) from exc
                    break
            except httpx.TransportError as exc:
                if attempt == self.settings.vllm_retries:
                    raise RuntimeError(f"vLLM request failed: {exc}") from exc
            if attempt == self.settings.vllm_retries:
                assert response is not None
                detail = response.text[:500]
                raise RuntimeError(f"vLLM returned HTTP {response.status_code}: {detail}")
            await asyncio.sleep(0.1 * (2**attempt))

        assert response is not None
        try:
            choices = response.json()["choices"]
            content = choices[0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("vLLM returned an invalid chat-completions response") from exc
        if not isinstance(content, str) or not content.strip():
            raise ValueError("vLLM returned an empty OCR response")
        return content.strip(), None


class LocalPaddleOCRVLRecognition:
    """Direct in-process recognition backend for local GPU inference."""

    TASK_PROMPTS = {
        ContentType.TEXT: "OCR with layout:",
        ContentType.TABLE: "Table Recognition:",
        ContentType.FORMULA: "Formula Recognition:",
        ContentType.CHART: "Chart Recognition:",
    }

    def __init__(
        self,
        model_id: str = "PaddlePaddle/PaddleOCR-VL-1.6",
        device: str = "cuda",
        max_new_tokens: int = 1024,
        torch_dtype: str = "auto",
    ) -> None:
        if max_new_tokens < 1:
            raise ValueError("LOCAL_MAX_NEW_TOKENS must be positive")
        self.model_id = model_id
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.torch_dtype = torch_dtype
        self._processor = None
        self._model = None
        self._load_lock = threading.Lock()
        # Most accelerator model objects are not safe to call concurrently.
        self._inference_lock = asyncio.Lock()

    def _ensure_loaded(self) -> None:
        if self._model is None:
            with self._load_lock:
                if self._model is not None:
                    return
                import transformers.masking_utils
                _orig_create_causal_mask = transformers.masking_utils.create_causal_mask

                def _patched_create_causal_mask(*args, **kwargs):
                    if "inputs_embeds" in kwargs and "input_embeds" not in kwargs:
                        kwargs["input_embeds"] = kwargs.pop("inputs_embeds")
                    return _orig_create_causal_mask(*args, **kwargs)

                transformers.masking_utils.create_causal_mask = _patched_create_causal_mask

                import torch
                from transformers import AutoModelForCausalLM, AutoProcessor

                if self.device.startswith("cuda") and not torch.cuda.is_available():
                    raise RuntimeError("DEVICE requests CUDA, but CUDA is unavailable")
                dtype = self._resolve_dtype(torch)

                self._processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True)
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    trust_remote_code=True,
                    torch_dtype=dtype,
                ).to(self.device).eval()

    def _resolve_dtype(self, torch):
        if self.torch_dtype == "auto":
            if self.device.startswith("cuda"):
                return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            return torch.float32
        dtype = getattr(torch, self.torch_dtype, None)
        if dtype not in {torch.float16, torch.bfloat16, torch.float32}:
            raise ValueError("LOCAL_TORCH_DTYPE must be auto, float16, bfloat16, or float32")
        if not self.device.startswith("cuda") and dtype in {torch.float16, torch.bfloat16}:
            raise ValueError("CPU local inference requires LOCAL_TORCH_DTYPE=float32 or auto")
        return dtype

    async def recognize(self, image: bytes, kind: ContentType) -> tuple[str, float | None]:
        async with self._inference_lock:
            return await asyncio.to_thread(self._recognize_sync, image, kind)

    def _recognize_sync(self, image: bytes, kind: ContentType) -> tuple[str, float | None]:
        import torch
        from PIL import Image

        self._ensure_loaded()
        with Image.open(io.BytesIO(image)) as source:
            pil_img = source.convert("RGB")
        prompt = self.TASK_PROMPTS.get(kind, "OCR with layout:")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        text = self._processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = self._processor(text=[text], images=[pil_img], return_tensors="pt")
        inputs = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}
        with torch.inference_mode():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )
        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
        decoded = self._processor.decode(generated_ids, skip_special_tokens=True).strip()
        if not decoded:
            raise ValueError("local model returned an empty OCR response")
        return decoded, None

