from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExtractedDocument(BaseModel):
    schema_id: Literal["boleto", "fatura", "generic"]
    schema_version: Literal["v1"] = "v1"
    fields: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_validation: bool


SCHEMA_BY_LAYOUT = {
    "boleto_caixa": "boleto",
    "boleto_bb": "boleto",
    "boleto_bradesco": "boleto",
    "fatura_energia": "fatura",
    "fatura_condominio": "fatura",
    "generic": "generic",
}
