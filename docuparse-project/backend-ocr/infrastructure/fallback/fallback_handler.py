# =============================================================================
# INFRASTRUCTURE: infrastructure/fallback/fallback_handler.py
# =============================================================================
# Lógica de fallback entre engines OCR.
#
# Origem: migrado de utils/ocr_fallback.py (Fase 4 do refactor).
# utils/ocr_fallback.py agora é shim que re-exporta desta localização.
#
# Por que isolado aqui:
#   Problema P6 do PRD — a lógica de fallback estava misturada com a orquestração
#   no router.py. Aqui ela é isolada como responsabilidade de infraestrutura:
#   sabe o que os engines retornam e como combiná-los, mas não sabe de negócio.
#
# Funções públicas:
#   should_trigger_fallback()  → decide se o resultado primário é suficiente
#   merge_fallback_result()    → combina resultados do primário e do fallback
#   is_engine_error_fallback() → detecta quando o engine falhou por erro
# =============================================================================

from typing import Any, Dict

from utils.validate_fields import compute_field_pipeline_quality, extract_avg_confidence


def _text_coverage_metrics(data: Dict[str, Any]) -> tuple[int, int]:
    raw_text = str(data.get("raw_text") or "").strip()
    text_length = int((data.get("_meta") or {}).get("text_length") or len(raw_text))
    token_count = len([token for token in raw_text.split() if token.strip()])
    return text_length, token_count


def _should_replace_raw_text(primary_data: Dict[str, Any], fallback_data: Dict[str, Any]) -> bool:
    primary_len, primary_tokens = _text_coverage_metrics(primary_data)
    fallback_len, fallback_tokens = _text_coverage_metrics(fallback_data)

    if fallback_len == 0:
        return False

    # Evita regressão como "0 1": fallback com cobertura muito menor não substitui texto primário.
    if primary_len > 0:
        if fallback_len < int(primary_len * 0.6):
            return False
        if fallback_tokens < max(3, int(primary_tokens * 0.6)):
            return False

    return True


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
    replace_raw_text = _should_replace_raw_text(primary_data, fallback_data)

    for key in ["document_info", "entities", "tables", "totals"]:
        fallback_value = fallback_data.get(key)
        if fallback_value not in (None, "", [], {}):
            merged[key] = fallback_value

    if replace_raw_text:
        for key in ["raw_text", "raw_text_fallback"]:
            fallback_value = fallback_data.get(key)
            if fallback_value not in (None, ""):
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
        "fallback_raw_text_replaced": replace_raw_text,
    }

    return merged
