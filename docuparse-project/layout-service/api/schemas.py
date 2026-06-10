from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ClassifyLayoutRequest(BaseModel):
    raw_text: str = Field("", description="Texto bruto produzido pelo OCR")
    document_type: str = Field("unknown", description="Tipo de documento classificado pelo OCR")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClassifyLayoutResponse(BaseModel):
    layout: str
    confidence: float = Field(ge=0.0, le=1.0)
    document_type: str
    requires_human_validation: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
