from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, Field, model_validator


class OCRMode(StrEnum):
    VLM = "vlm"
    HYBRID = "hybrid"
    LEGACY = "legacy"


class ContentType(StrEnum):
    TEXT = "text"
    TABLE = "table"
    FORMULA = "formula"
    CHART = "chart"


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

    @model_validator(mode="after")
    def ordered(self) -> "BoundingBox":
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("bounding box must have positive area")
        return self


class OCRBlock(BaseModel):
    page: int = Field(ge=1)
    order: int = Field(ge=0)
    kind: ContentType
    bbox: BoundingBox
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    engine: str


class OCRDocument(BaseModel):
    model_id: str
    model_revision: str
    blocks: list[OCRBlock]
    markdown: str


class OCRRequest(BaseModel):
    content_base64: str = Field(min_length=1)
    filename: str = Field(min_length=1, max_length=255)
    mode: OCRMode = OCRMode.VLM
