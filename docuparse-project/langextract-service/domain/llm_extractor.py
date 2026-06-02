"""LLM-based field extractor that uses a SchemaConfig definition to guide extraction.

The SchemaConfig.definition produced by the frontend Settings tab has this shape:
    {
        "schema_id": "nota_fiscal",
        "version": "v1",
        "fields": [
            {"name": "numero_nota", "type": "string", "required": true, "rule": "..."},
            {"name": "valor_total", "type": "decimal", "required": true, "rule": "..."}
        ],
        "prompt": {"instructions": "..."},
        "examples": [{"field": "...", "expected": "...", "source": "..."}]
    }

The LLM is called via the OpenRouter chat-completions API using the same env vars
already present in backend-ocr:
    OPENROUTER_API_KEY
    OPENROUTER_MODEL
    OPENROUTER_BASE_URL   (optional, defaults to https://openrouter.ai/api/v1)
    OPENROUTER_TIMEOUT    (optional, default 60 s)

When the LLM call fails, every expected field is filled with EXTRACTION_NOT_FOUND
so the human-validation step sees all fields with a clear placeholder.

Environment variables:
    OPENROUTER_API_KEY   — required for LLM extraction
    OPENROUTER_MODEL     — required for LLM extraction
    OPENROUTER_BASE_URL  — OpenRouter base URL (optional)
    OPENROUTER_TIMEOUT   — request timeout in seconds (optional)
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any

from domain.schemas import ExtractedDocument

logger = logging.getLogger(__name__)

# Placeholder written into fields that the LLM could not locate in the document.
# Using a non-empty string ensures the field appears in the validation UI so the
# human reviewer knows it still needs to be filled.
EXTRACTION_NOT_FOUND = "Valor não encontrado"


def extract_with_llm(
    raw_text: str,
    schema_definition: dict[str, Any],
    *,
    tenant_id: str = "unknown",
    confidence_threshold: float = 0.75,
) -> ExtractedDocument:
    """Extract fields from raw_text using an LLM guided by schema_definition.

    Falls back gracefully:
    - If OPENROUTER_API_KEY is unset  → returns all fields as EXTRACTION_NOT_FOUND
    - If LLM call or JSON parse fails  → same placeholder behaviour
    """
    schema_id = schema_definition.get("schema_id") or "generic"
    schema_version = schema_definition.get("version") or "v1"
    fields_spec: list[dict] = schema_definition.get("fields") or []
    instructions: str = (schema_definition.get("prompt") or {}).get("instructions") or ""
    examples: list[dict] = schema_definition.get("examples") or []

    field_names = [f["name"] for f in fields_spec if f.get("name")]

    if not field_names:
        logger.warning(
            "langextract.llm_extractor.no_fields_defined | schema_id=%s tenant=%s",
            schema_id, tenant_id,
        )
        return ExtractedDocument(
            schema_id=schema_id,
            schema_version=schema_version,
            fields={},
            confidence=0.0,
            requires_human_validation=True,
        )

    # Build the extraction prompt from the schema definition
    prompt = _build_extraction_prompt(raw_text, instructions, fields_spec, examples)

    # Call the LLM
    try:
        raw_response = _call_openrouter(prompt)
        extracted_fields = _parse_llm_response(raw_response, field_names)
        logger.info(
            "langextract.llm_extractor.llm_call_success | schema_id=%s tenant=%s "
            "fields_returned=%d",
            schema_id, tenant_id, len(extracted_fields),
        )
    except Exception as exc:
        logger.error(
            "langextract.llm_extractor.llm_call_failed | schema_id=%s tenant=%s error=%s",
            schema_id, tenant_id, exc,
        )
        extracted_fields = {name: {"value": None, "confidence": 0.0} for name in field_names}

    # Replace missing/null values with EXTRACTION_NOT_FOUND so each field appears in the UI
    for name in field_names:
        entry = extracted_fields.get(name)
        val = entry.get("value") if isinstance(entry, dict) else entry
        if val is None:
            extracted_fields[name] = {"value": EXTRACTION_NOT_FOUND, "confidence": 0.0}

    # Log the full list of extracted fields for observability
    logger.info(
        "langextract.llm_extractor.fields_produced | schema_id=%s tenant=%s | %s",
        schema_id,
        tenant_id,
        {k: v for k, v in extracted_fields.items()},
    )

    confidence = _calculate_confidence(extracted_fields, fields_spec)

    return ExtractedDocument(
        schema_id=schema_id,
        schema_version=schema_version,
        fields=extracted_fields,
        confidence=confidence,
        requires_human_validation=confidence < confidence_threshold,
    )


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_extraction_prompt(
    raw_text: str,
    instructions: str,
    fields_spec: list[dict],
    examples: list[dict],
) -> str:
    """Compose the user-facing extraction prompt sent to the LLM."""

    # Describe each field (name, type, required flag, extraction rule)
    fields_lines = []
    for f in fields_spec:
        name = f.get("name", "")
        if not name:
            continue
        ftype = f.get("type", "string")
        required_mark = "*" if f.get("required") else ""
        rule = f.get("rule", "")
        rule_part = f" — {rule}" if rule else ""
        fields_lines.append(f"  - {name}{required_mark} ({ftype}){rule_part}")
    fields_block = "\n".join(fields_lines)

    # Include up to 5 annotated examples to guide the LLM
    examples_block = ""
    if examples:
        ex_lines = []
        for ex in examples[:5]:
            field = ex.get("field", "")
            expected = ex.get("expected", "")
            source = ex.get("source", "")
            ex_lines.append(f'  - campo "{field}": valor "{expected}" extraído de "{source}"')
        examples_block = "\n\nExemplos anotados:\n" + "\n".join(ex_lines)

    # Expected JSON template with per-field value and confidence
    json_template = json.dumps(
        {name: {"value": "<valor extraído ou null>", "confidence": 0.0} for name in [f["name"] for f in fields_spec if f.get("name")]},
        ensure_ascii=False,
        indent=2,
    )

    # Truncate very long documents to save tokens (keep first 8 000 chars)
    raw_text_truncated = raw_text[:8000]
    if len(raw_text) > 8000:
        raw_text_truncated += "\n[... texto truncado ...]"

    return f"""## Instruções de extração:
{instructions}

## Campos para extrair (* = obrigatório):
{fields_block}
{examples_block}

## Texto do documento:
{raw_text_truncated}

## Tarefa:
Extraia os campos listados acima do texto do documento seguindo as instruções.
Para cada campo, retorne um objeto com:
- "value": o valor encontrado no texto (string, número, ou null se não encontrado)
- "confidence": número entre 0 e 1 indicando sua confiança na extração
  - 0.95–1.0: valor explícito e inequívoco no texto
  - 0.70–0.94: valor claro com pequena ambiguidade
  - 0.40–0.69: valor inferido com alguma incerteza
  - 0.0: campo não encontrado (use junto com value: null)

Regras:
- Retorne o valor exatamente como aparece no texto (sem inventar).
- Se não encontrar o campo, retorne {{"value": null, "confidence": 0.0}}.
- Não repita o texto completo, somente o valor do campo.

Retorne APENAS um objeto JSON válido com o seguinte formato, sem qualquer texto adicional:
{json_template}"""


# ---------------------------------------------------------------------------
# OpenRouter HTTP call
# ---------------------------------------------------------------------------

def _call_openrouter(user_prompt: str) -> str:
    """Call the OpenRouter chat-completions API and return the assistant message."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    # LANGEXTRACT_MODEL is the dedicated env var for text extraction.
    # We deliberately do NOT fall back to OPENROUTER_MODEL because that variable is
    # shared with backend-ocr and may point to a vision-only model (e.g.
    # baidu/qianfan-ocr-fast:free) that rejects text chat-completion requests.
    # The hardcoded default ensures a capable text model is always available even
    # when the container hasn't picked up the env var yet.
    
    model = os.getenv("LANGEXTRACT_MODEL")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    timeout = int(os.getenv("OPENROUTER_TIMEOUT", "60"))

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set — LLM extraction is disabled")
    if not model:
        raise RuntimeError("LANGEXTRACT_MODEL is not set — LLM extraction is disabled")

    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 4096,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Você é um assistente de extração de dados estruturados. "
                    "Extrai campos de documentos e retorna APENAS JSON válido, "
                    "sem explicações nem texto adicional."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
    }

    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    site_url = os.getenv("OPENROUTER_SITE_URL", "").strip()
    app_name = os.getenv("OPENROUTER_APP_NAME", "docuparse-langextract").strip()
    if site_url:
        headers["HTTP-Referer"] = site_url
    if app_name:
        headers["X-Title"] = app_name

    url = f"{base_url.rstrip('/')}/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    logger.info(
        "langextract.llm_extractor.openrouter_call | model=%s url=%s", model, url
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as http_err:
        error_body = ""
        try:
            error_body = http_err.read().decode("utf-8")
        except Exception:
            pass
        logger.error(
            "langextract.llm_extractor.openrouter_http_error | model=%s status=%s body=%s",
            model, http_err.code, error_body[:500],
        )
        raise RuntimeError(f"OpenRouter HTTP {http_err.code}: {error_body[:200]}") from http_err

    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError(f"OpenRouter returned empty choices: {body}")

    content = (choices[0].get("message") or {}).get("content") or ""
    if not content:
        raise RuntimeError("OpenRouter returned empty content")

    logger.debug("langextract.llm_extractor.raw_response | %.500s", content)
    return content


# ---------------------------------------------------------------------------
# JSON response parsing
# ---------------------------------------------------------------------------

def _parse_llm_response(raw_response: str, field_names: list[str]) -> dict[str, Any]:
    """Parse LLM response into {field: {value, confidence}} structure.

    Strategy:
    1. Full JSON parse — normalizes any field to {value, confidence} dict,
       preserving confidence scores returned by the LLM.
    2. If JSON is truncated or malformed, regex-based partial recovery so fields
       that were already emitted before the truncation point are not lost.
    """
    content = raw_response.strip()

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    if "```json" in content:
        content = content.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in content:
        content = content.split("```", 1)[1].split("```", 1)[0].strip()

    # Find the outermost JSON object
    start = content.find("{")
    end = content.rfind("}") + 1
    json_content = content[start:end] if start >= 0 and end > start else content

    # Attempt 1: full JSON parse
    try:
        parsed = json.loads(json_content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response is not a JSON object")

        result = {name: _normalize_field_entry(parsed.get(name)) for name in field_names}
        logger.info(
            "langextract.llm_extractor.parsed_fields | fields=%s", list(result.keys())
        )
        return result
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning(
            "langextract.llm_extractor.json_parse_failed | error=%s raw=%.300s",
            exc, raw_response,
        )

    # Attempt 2: regex-based partial recovery for truncated responses
    result = _recover_partial_fields(raw_response, field_names)
    found = sum(1 for v in result.values() if v is not None)
    if found > 0:
        logger.info(
            "langextract.llm_extractor.partial_recovery_success | fields_recovered=%d/%d",
            found, len(field_names),
        )
        return result

    logger.warning("langextract.llm_extractor.recovery_failed | returning all fields as None")
    return {name: None for name in field_names}


def _normalize_field_entry(value: Any) -> dict[str, Any]:
    """Normalize any LLM field response to {value, confidence} structure."""
    if isinstance(value, dict) and "value" in value:
        raw_conf = value.get("confidence")
        confidence = raw_conf if isinstance(raw_conf, (int, float)) else None
        return {"value": value.get("value"), "confidence": confidence}
    return {"value": value, "confidence": None}


def _recover_partial_fields(text: str, field_names: list[str]) -> dict[str, Any]:
    """Regex recovery for truncated/malformed JSON — handles both flat and nested formats.

    Patterns matched:
      "field": {"value": "string", ...}   — nested with confidence score
      "field": {"value": null, ...}        — nested null
      "field": "direct value"              — flat string
      "field": null                        — flat null
    """
    result: dict[str, Any] = {name: None for name in field_names}
    if not field_names:
        return result

    names_pat = "|".join(re.escape(n) for n in field_names)

    # Nested: "field": {"value": "...", "confidence": 0.9, ...} or {"value": null, ...}
    nested_re = re.compile(
        r'"(' + names_pat + r')"\s*:\s*\{\s*"value"\s*:\s*(?:"([^"]*)"|(null))\b'
    )
    for m in nested_re.finditer(text):
        name = m.group(1)
        result[name] = {"value": None if m.group(3) else m.group(2), "confidence": None}

    # Flat string: "field": "value"  (only fills fields not yet recovered)
    flat_str_re = re.compile(r'"(' + names_pat + r')"\s*:\s*"([^"]*)"')
    for m in flat_str_re.finditer(text):
        name = m.group(1)
        if result[name] is None:
            result[name] = {"value": m.group(2), "confidence": None}

    # Flat null: "field": null  (only fills fields not yet recovered)
    flat_null_re = re.compile(r'"(' + names_pat + r')"\s*:\s*null\b')
    for m in flat_null_re.finditer(text):
        name = m.group(1)
        if result[name] is None:
            result[name] = None  # explicit null keeps as None → becomes placeholder later

    return result


# ---------------------------------------------------------------------------
# Confidence calculation
# ---------------------------------------------------------------------------

def _calculate_confidence(
    fields: dict[str, Any],
    fields_spec: list[dict],
) -> float:
    """Confidence = fraction of required fields with a real (non-placeholder) value.

    Falls back to all fields when no required fields are defined.
    """
    required_names = [f["name"] for f in fields_spec if f.get("required") and f.get("name")]
    target_names = required_names or [f["name"] for f in fields_spec if f.get("name")]

    if not target_names:
        return 0.0

    def _get_field_value(entry: Any) -> Any:
        if isinstance(entry, dict) and "value" in entry:
            return entry["value"]
        return entry

    present = sum(
        1 for name in target_names
        if _get_field_value(fields.get(name)) and _get_field_value(fields.get(name)) != EXTRACTION_NOT_FOUND
    )
    return round(present / len(target_names), 2)
