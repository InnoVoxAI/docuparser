from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    raw_text: str = ""
    layout: str = "generic"
    document_type: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractResponse(BaseModel):
    schema_id: str
    schema_version: str
    fields: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_validation: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
