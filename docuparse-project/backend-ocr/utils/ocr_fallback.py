from typing import Any, Dict

from utils.validate_fields import extract_avg_confidence


def should_trigger_fallback(data: Dict[str, Any], min_confidence: float = 70.0) -> bool:
    avg_confidence = extract_avg_confidence(data)
    return avg_confidence is not None and avg_confidence < min_confidence


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