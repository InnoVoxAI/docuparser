from typing import Any, Dict, List, Tuple
import re


REQUIRED_FIELDS = [
    "fornecedor",
    "tomador",
    "cnpj_fornecedor",
    "numero_nf",
    "descricao_servico",
    "valor_nf",
    "retencao",
]


FIELD_VALIDATION_KEYS = {
    "fornecedor": "fornecedor_ok",
    "tomador": "tomador_ok",
    "cnpj_fornecedor": "cnpj_fornecedor_valido",
    "cnpj_tomador": "cnpj_tomador_valido",
    "numero_nf": "numero_nf_valido",
    "descricao_servico": "descricao_ok",
    "valor_nf": "valor_valido",
    "retencao": "retencao_ok",
}


def _normalize_digits(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _validate_cnpj(cnpj: str | None) -> bool:
    digits = _normalize_digits(cnpj or "")
    if len(digits) != 14:
        return False

    if len(set(digits)) == 1:
        return False

    def _calc_digit(base: str, weights: List[int]) -> str:
        total = sum(int(num) * weight for num, weight in zip(base, weights))
        remainder = total % 11
        digit = 0 if remainder < 2 else 11 - remainder
        return str(digit)

    first = _calc_digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = _calc_digit(digits[:12] + first, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])

    return digits[-2:] == f"{first}{second}"


def _get_raw_text(data: Dict[str, Any]) -> str:
    return str(data.get("raw_text") or data.get("raw_text_fallback") or "")


def _extract_line_value_by_labels(raw_text: str, labels: List[str]) -> str:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    for line in lines:
        lowered = line.lower()
        if any(label in lowered for label in labels):
            parts = re.split(r"[:\-]\s*", line, maxsplit=1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()

            for label in labels:
                idx = lowered.find(label)
                if idx >= 0:
                    candidate = line[idx + len(label):].strip(" :-")
                    if candidate:
                        return candidate

    return ""


def _extract_cnpj_from_text(raw_text: str, preferred_labels: List[str]) -> str:
    cnpj_pattern = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    for line in lines:
        lowered = line.lower()
        if any(label in lowered for label in preferred_labels):
            match = cnpj_pattern.search(line)
            if match:
                return match.group(0)

    match = cnpj_pattern.search(raw_text)
    return match.group(0) if match else ""


def _extract_numero_nf(raw_text: str, document_info: Dict[str, Any]) -> str:
    doc_number = str(document_info.get("number") or "").strip()
    if doc_number:
        return doc_number

    patterns = [
        r"(?:n[úu]mero\s*(?:da\s*)?(?:nfs-?e|nfse|nota\s*fiscal)|n[º°o]?\s*(?:da\s*)?(?:nfs-?e|nfse|nota\s*fiscal))\s*[:#\-]?\s*([A-Za-z0-9./-]+)",
        r"(?:nota\s*fiscal\s*n[º°o]?|nf\s*n[º°o]?)\s*[:#\-]?\s*([A-Za-z0-9./-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return ""


def _extract_valor_nf(raw_text: str, totals: Dict[str, Any]) -> str:
    grand_total = totals.get("grand_total")
    if grand_total not in (None, ""):
        return str(grand_total)

    patterns = [
        r"(?:valor\s*(?:total)?\s*(?:da\s*)?nota|valor\s*(?:da\s*)?nfs-?e)\s*[:\-]?\s*(R\$\s*)?([\d\.]+,\d{2}|\d+\.\d{2}|\d+)",
        r"(?:total\s*a\s*pagar|valor\s*líquido)\s*[:\-]?\s*(R\$\s*)?([\d\.]+,\d{2}|\d+\.\d{2}|\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw_text, flags=re.IGNORECASE)
        if match:
            return match.group(2).strip()

    return ""


def _extract_descricao_servico(raw_text: str) -> str:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        lowered = line.lower()
        if "descrição" in lowered and "serv" in lowered:
            parts = re.split(r"[:\-]\s*", line, maxsplit=1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()

            if index + 1 < len(lines):
                return lines[index + 1]

    return ""


def _extract_retencao(raw_text: str) -> str:
    retention_terms = ["reten", "iss", "inss", "pis", "cofins", "csll", "irrf"]
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    retention_lines = [line for line in lines if any(term in line.lower() for term in retention_terms)]
    if retention_lines:
        return " | ".join(retention_lines[:4])

    return ""


def _parse_currency(value: str | float | int | None) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    normalized = str(value).strip()
    if not normalized:
        return None

    normalized = normalized.replace("R$", "").replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", ".")

    try:
        return float(normalized)
    except ValueError:
        return None


def extract_critical_fields(data: Dict[str, Any]) -> Dict[str, str]:
    raw_text = _get_raw_text(data)
    entities = data.get("entities") if isinstance(data.get("entities"), dict) else {}
    document_info = data.get("document_info") if isinstance(data.get("document_info"), dict) else {}
    totals = data.get("totals") if isinstance(data.get("totals"), dict) else {}

    fornecedor = str(
        entities.get("issuer")
        or entities.get("fornecedor")
        or entities.get("prestador")
        or _extract_line_value_by_labels(raw_text, ["fornecedor", "prestador", "emitente", "emissor"])
        or ""
    ).strip()

    tomador = str(
        entities.get("recipient")
        or entities.get("tomador")
        or entities.get("destinatario")
        or _extract_line_value_by_labels(raw_text, ["tomador", "destinatário", "destinatario", "cliente"])
        or ""
    ).strip()

    cnpj_fornecedor = str(
        entities.get("cnpj_fornecedor")
        or entities.get("issuer_cnpj")
        or _extract_cnpj_from_text(raw_text, ["fornecedor", "prestador", "emitente", "emissor"])
        or ""
    ).strip()

    cnpj_tomador = str(
        entities.get("cnpj_tomador")
        or entities.get("recipient_cnpj")
        or _extract_cnpj_from_text(raw_text, ["tomador", "destinatário", "destinatario", "cliente"])
        or ""
    ).strip()

    if cnpj_fornecedor and cnpj_tomador and _normalize_digits(cnpj_fornecedor) == _normalize_digits(cnpj_tomador):
        cnpj_tomador = ""

    numero_nf = _extract_numero_nf(raw_text, document_info)
    descricao_servico = _extract_descricao_servico(raw_text)
    valor_nf = _extract_valor_nf(raw_text, totals)
    retencao = _extract_retencao(raw_text)

    return {
        "fornecedor": fornecedor,
        "tomador": tomador,
        "cnpj_fornecedor": cnpj_fornecedor,
        "cnpj_tomador": cnpj_tomador,
        "numero_nf": numero_nf,
        "descricao_servico": descricao_servico,
        "valor_nf": valor_nf,
        "retencao": retencao,
    }


def validate_fields(fields: Dict[str, str]) -> Dict[str, bool]:
    fornecedor = str(fields.get("fornecedor") or "").strip()
    tomador = str(fields.get("tomador") or "").strip()
    cnpj_fornecedor = str(fields.get("cnpj_fornecedor") or "").strip()
    cnpj_tomador = str(fields.get("cnpj_tomador") or "").strip()
    numero_nf = str(fields.get("numero_nf") or "").strip()
    descricao_servico = str(fields.get("descricao_servico") or "").strip()
    retencao = str(fields.get("retencao") or "").strip()
    valor_nf = _parse_currency(fields.get("valor_nf"))

    validation = {
        "fornecedor_ok": len(fornecedor) > 2,
        "tomador_ok": len(tomador) > 2,
        "cnpj_fornecedor_valido": _validate_cnpj(cnpj_fornecedor),
        "cnpj_tomador_valido": _validate_cnpj(cnpj_tomador) if cnpj_tomador else False,
        "numero_nf_valido": bool(numero_nf),
        "descricao_ok": len(descricao_servico) > 10,
        "valor_valido": valor_nf is not None and valor_nf > 0,
        "retencao_ok": len(retencao) > 0,
    }

    validation["required_fields_present"] = {
        field_name: bool(str(fields.get(field_name) or "").strip())
        for field_name in REQUIRED_FIELDS
    }
    validation["cnpj_tomador_validado"] = validation["cnpj_tomador_valido"]

    return validation


def extract_avg_confidence(data: Dict[str, Any]) -> float | None:
    if not isinstance(data, dict):
        return None

    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    candidates = [
        meta.get("avg_confidence"),
        meta.get("average_confidence"),
        meta.get("confidence"),
        data.get("avg_confidence"),
    ]

    for candidate in candidates:
        if candidate is None:
            continue

        try:
            value = float(candidate)
        except (TypeError, ValueError):
            continue

        if 0.0 <= value <= 1.0:
            value *= 100.0

        return max(0.0, min(100.0, value))

    return None


def compute_field_pipeline_quality(
    data: Dict[str, Any],
    override_fields: Dict[str, str] | None = None,
    override_ocr_confidence: float | None = None,
) -> Dict[str, Any]:
    fields = override_fields or extract_critical_fields(data)
    validation = validate_fields(fields)

    validation_flags = [
        bool(value)
        for key, value in validation.items()
        if key != "required_fields_present" and isinstance(value, bool)
    ]
    field_score = (sum(validation_flags) / len(validation_flags)) if validation_flags else 0.0

    ocr_confidence_pct = override_ocr_confidence if override_ocr_confidence is not None else (extract_avg_confidence(data) or 0.0)
    ocr_confidence = max(0.0, min(100.0, float(ocr_confidence_pct))) / 100.0
    final_score = (0.4 * ocr_confidence) + (0.6 * field_score)

    required_present = validation.get("required_fields_present", {})
    missing_required = any(not bool(required_present.get(field_name)) for field_name in REQUIRED_FIELDS)
    critical_invalid = any(
        not bool(validation.get(key))
        for key in ["cnpj_fornecedor_valido", "valor_valido", "numero_nf_valido"]
    )

    return {
        "fields": fields,
        "validation": validation,
        "ocr_confidence": round(ocr_confidence, 4),
        "field_score": round(field_score, 4),
        "final_score": round(final_score, 4),
        "fallback_needed": critical_invalid or missing_required or final_score < 0.85,
    }


def merge_fields_by_validation(
    primary_fields: Dict[str, str],
    fallback_fields: Dict[str, str],
    fallback_validation: Dict[str, Any],
) -> Tuple[Dict[str, str], List[str]]:
    merged = dict(primary_fields)
    fields_from_fallback: List[str] = []

    for field_name, validation_key in FIELD_VALIDATION_KEYS.items():
        fallback_value = str(fallback_fields.get(field_name) or "").strip()
        if not fallback_value:
            continue

        fallback_valid = bool(fallback_validation.get(validation_key))
        primary_empty = not str(primary_fields.get(field_name) or "").strip()

        if fallback_valid or primary_empty:
            merged[field_name] = fallback_value
            fields_from_fallback.append(field_name)

    for field_name in REQUIRED_FIELDS:
        merged.setdefault(field_name, "")

    merged.setdefault("cnpj_tomador", str(primary_fields.get("cnpj_tomador") or "").strip())
    return merged, fields_from_fallback


def resolve_field_fallback_engine(classification: str, primary_engine: str) -> str | None:
    preferred = {
        "digital_pdf": "llamaparse",
        "scanned_image": "easyocr",
        "handwritten_complex": "deepseek",
    }
    alternatives = {
        "llamaparse": "docling",
        "easyocr": "tesseract",
        "deepseek": "paddle",
        "paddle": "easyocr",
        "docling": "llamaparse",
        "tesseract": "easyocr",
    }

    normalized_primary = primary_engine.lower().strip()
    if normalized_primary == "paddle_deepseek":
        normalized_primary = "paddle"

    candidate = preferred.get(classification)
    if not candidate:
        return None

    if candidate == normalized_primary:
        return alternatives.get(candidate)

    return candidate