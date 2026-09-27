from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExtractedDocument(BaseModel):
    # schema_id is now any string so dynamic schemas from SchemaConfig are accepted
    schema_id: str
    schema_version: str = "v1"
    fields: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_validation: bool
