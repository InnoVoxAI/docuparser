from __future__ import annotations

import re

from domain.schemas import SCHEMA_BY_LAYOUT, ExtractedDocument


def extract_fields(raw_text: str, layout: str, document_type: str = "unknown") -> ExtractedDocument:
    schema_id = SCHEMA_BY_LAYOUT.get(layout, "generic")
    if schema_id == "boleto":
        fields, confidence = _extract_boleto(raw_text)
    elif schema_id == "fatura":
        fields, confidence = _extract_fatura(raw_text)
    else:
        fields, confidence = {"raw_text_preview": raw_text[:500]}, 0.25 if raw_text else 0.0

    return ExtractedDocument(
        schema_id=schema_id,
        schema_version="v1",
        fields=fields,
        confidence=round(confidence, 2),
        requires_human_validation=confidence < 0.75,
    )


def _extract_boleto(raw_text: str) -> tuple[dict[str, str | None], float]:
    fields = {
        "linha_digitavel": _first_match(raw_text, r"(\d{5}\.?\d{5}\s+\d{5}\.?\d{6}\s+\d{5}\.?\d{6}\s+\d\s+\d{14})"),
        "vencimento": _first_match(raw_text, r"\b(\d{2}[/-]\d{2}[/-]\d{2,4})\b"),
        "valor": _first_match(raw_text, r"(?:valor|total)\s*[:\-]?\s*(R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}|\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE),
        "beneficiario": _first_match(raw_text, r"(?:benefici[aá]rio|cedente)\s*[:\-]?\s*([A-Za-z0-9 .&/-]{3,80})", re.IGNORECASE),
    }
    return fields, _confidence(fields)


def _extract_fatura(raw_text: str) -> tuple[dict[str, str | None], float]:
    fields = {
        "vencimento": _first_match(raw_text, r"\b(\d{2}[/-]\d{2}[/-]\d{2,4})\b"),
        "valor": _first_match(raw_text, r"(?:valor|total)\s*[:\-]?\s*(R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}|\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE),
        "unidade": _first_match(raw_text, r"(?:unidade|uc)\s*[:\-]?\s*([A-Za-z0-9 .&/-]{2,40})", re.IGNORECASE),
        "consumo_kwh": _first_match(raw_text, r"(\d+(?:,\d+)?)\s*kwh", re.IGNORECASE),
    }
    return fields, _confidence(fields)


def _first_match(raw_text: str, pattern: str, flags: int = 0) -> str | None:
    match = re.search(pattern, raw_text or "", flags)
    if not match:
        return None
    return match.group(1).strip()


def _confidence(fields: dict[str, str | None]) -> float:
    if not fields:
        return 0.0
    present = sum(1 for value in fields.values() if value)
    return present / len(fields)
