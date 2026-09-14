from __future__ import annotations

import base64
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

    async def recognize(self, image: bytes, kind: ContentType) -> tuple[str, float | None]:
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
            "temperature": 0,
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(f"{self.settings.vllm_base_url}/chat/completions", json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
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

    def __init__(self, model_id: str = "PaddlePaddle/PaddleOCR-VL-1.6", device: str = "cuda") -> None:
        self.model_id = model_id
        self.device = device
        self._processor = None
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            import transformers.masking_utils
            _orig_create_causal_mask = transformers.masking_utils.create_causal_mask

            def _patched_create_causal_mask(*args, **kwargs):
                if "inputs_embeds" in kwargs and "input_embeds" not in kwargs:
                    kwargs["input_embeds"] = kwargs.pop("inputs_embeds")
                return _orig_create_causal_mask(*args, **kwargs)

            transformers.masking_utils.create_causal_mask = _patched_create_causal_mask

            import torch
            from transformers import AutoModelForCausalLM, AutoProcessor

            self._processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                trust_remote_code=True,
                torch_dtype=torch.bfloat16,
            ).to(self.device)

    async def recognize(self, image: bytes, kind: ContentType) -> tuple[str, float | None]:
        import io
        import torch
        from PIL import Image

        self._ensure_loaded()
        pil_img = Image.open(io.BytesIO(image)).convert("RGB")
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
                max_new_tokens=1024,
                do_sample=False,
            )
        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
        decoded = self._processor.decode(generated_ids, skip_special_tokens=True).strip()
        return decoded, None

