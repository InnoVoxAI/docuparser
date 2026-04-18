from typing import Any, Dict

from utils.validate_fields import compute_field_pipeline_quality, extract_avg_confidence


def _has_low_text_coverage(data: Dict[str, Any]) -> bool:
    raw_text = str(data.get("raw_text") or "").strip()
    text_length = int((data.get("_meta") or {}).get("text_length") or len(raw_text))
    token_count = len([token for token in raw_text.split() if token.strip()])

    input_meta = data.get("input_meta") if isinstance(data.get("input_meta"), dict) else {}
    page_count = int(input_meta.get("pdf_page_count") or input_meta.get("stacked_pages") or 1)
    chars_per_page = text_length / max(1, page_count)

    # Ajuste de cobertura: pouco texto total, baixa densidade por página ou poucos tokens distintos.
    low_total_text = text_length < 80
    low_density_for_pdf = page_count >= 2 and chars_per_page < 90
    low_tokens = token_count < 15

    return low_total_text or low_density_for_pdf or low_tokens


def should_trigger_fallback(data: Dict[str, Any], min_confidence: float = 70.0) -> bool:
    # Ajuste de fallback: considera qualidade por campo além da confiança média do OCR.
    avg_confidence = extract_avg_confidence(data)
    low_avg_confidence = avg_confidence is not None and avg_confidence < min_confidence

    quality = compute_field_pipeline_quality(data)
    field_driven_fallback = bool(quality.get("fallback_needed"))
    low_coverage_fallback = _has_low_text_coverage(data)

    return low_avg_confidence or field_driven_fallback or low_coverage_fallback


def is_engine_error_fallback(data: Dict[str, Any]) -> bool:
    if not isinstance(data, dict):
        return True

    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    if meta.get("error"):
        return True

    raw_text_fallback = str(data.get("raw_text_fallback", "") or "")
    return raw_text_fallback.startswith("Failed to process with")


def merge_fallback_result(
    primary_data: Dict[str, Any],
    fallback_data: Dict[str, Any],
    primary_engine: str,
    fallback_engine: str,
) -> Dict[str, Any]:
    merged = dict(primary_data)

    for key in ["document_info", "entities", "tables", "totals", "raw_text", "raw_text_fallback"]:
        fallback_value = fallback_data.get(key)
        if fallback_value not in (None, "", [], {}):
            merged[key] = fallback_value

    primary_meta = primary_data.get("_meta") if isinstance(primary_data.get("_meta"), dict) else {}
    fallback_meta = fallback_data.get("_meta") if isinstance(fallback_data.get("_meta"), dict) else {}

    merged["_meta"] = {
        **primary_meta,
        **fallback_meta,
        "primary_engine": primary_engine,
        "fallback_engine": fallback_engine,
        "primary_avg_confidence": extract_avg_confidence(primary_data),
        "fallback_triggered": True,
    }

    return merged