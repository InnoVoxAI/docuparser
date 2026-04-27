"""OpenRouter OCR engine — adapted from scripts/ocr_openrouter_pipeline.py.

Works with bytes (no file-path dependency) so it fits the backend-ocr
engine interface.  Flow mirrors the original script:

  PDF with text layer  → Docling (DoclingEngine) → raw_text
  PDF as image         → render pages → OpenRouter vision LLM → raw_text
  Image file           → OpenRouter vision LLM → raw_text

Environment variables required for the vision path:
  OPENROUTER_API_KEY   — Bearer token
  OPENROUTER_MODEL     — e.g. "google/gemini-flash-1.5"

Optional:
  OPENROUTER_BASE_URL  (default https://openrouter.ai/api/v1)
  OPENROUTER_SITE_URL
  OPENROUTER_APP_NAME
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any, Dict, List

import cv2
import fitz  # pymupdf
import numpy as np
import requests
from PIL import Image

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

_DoclingEngine = None  # lazy import to avoid loading Docling at startup


# ── PDF classification ──────────────────────────────────────────────────────

def _classify_pdf_bytes(content: bytes) -> Dict[str, Any]:
    """Mirrors classify_pdf() from ocr_openrouter_pipeline.py but uses bytes."""
    doc = fitz.open(stream=content, filetype="pdf")
    txtblocks = imgblocks = 0
    docfonts: List[str] = []

    for page in doc:
        for block in page.get_text("dict").get("blocks", []):
            btype = block.get("type")
            if btype == 0:
                txtblocks += 1
            elif btype == 1:
                imgblocks += 1
        for font in page.get_fonts():
            fname = font[3]
            if fname not in docfonts:
                docfonts.append(fname)

    nr_pages = len(doc)
    doc.close()

    mode = "text" if txtblocks > 0 and txtblocks >= imgblocks else "image"
    return {
        "nr_pages": nr_pages,
        "txtblocks": txtblocks,
        "imgblocks": imgblocks,
        "docfonts": docfonts,
        "mode": mode,
    }


# ── Text-PDF extraction ─────────────────────────────────────────────────────

def _extract_text_with_docling(content: bytes) -> str:
    """Delegates to the existing DoclingEngine that already handles PDF bytes."""
    global _DoclingEngine
    if _DoclingEngine is None:
        from engines.docling_engine import DoclingEngine
        _DoclingEngine = DoclingEngine

    engine = _DoclingEngine()
    result = engine.process(content)
    return result.get("raw_text") or result.get("raw_text_fallback") or ""


def _extract_text_with_pymupdf(content: bytes) -> str:
    """Fallback: extract text layer directly with PyMuPDF."""
    doc = fitz.open(stream=content, filetype="pdf")
    pages = [(page.get_text("text") or "").strip() for page in doc]
    doc.close()
    return "\n\n".join(t for t in pages if t).strip()


# ── Image rendering ─────────────────────────────────────────────────────────

def _render_pdf_as_images(content: bytes, dpi: int = 300) -> List[Any]:
    """Render every PDF page to a BGR numpy array."""
    doc = fitz.open(stream=content, filetype="pdf")
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
    doc.close()
    return images


# ── OpenRouter helpers ───────────────────────────────────────────────────────

def _to_data_url(image_bgr: Any, quality: int = 90) -> str:
    ok, encoded = cv2.imencode(".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("Failed to encode image to JPEG")
    b64 = base64.b64encode(encoded.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _extract_text_from_partial_json(text: str) -> str:
    """Recover extracted_text from a JSON string truncated by token-limit mid-value."""
    match = re.search(r'"extracted_text"\s*:\s*"((?:[^"\\]|\\.)*)', text, re.DOTALL)
    if not match:
        return ""
    raw = match.group(1)
    raw = (
        raw.replace("\\n", "\n")
           .replace("\\t", "\t")
           .replace('\\"', '"')
           .replace("\\\\", "\\")
           .replace("\\/", "/")
    )
    return raw.strip()


def _remove_loop_repetitions(text: str, min_phrase: int = 15) -> str:
    """Truncate text at the first looping repetition (≥3 exact consecutive occurrences)."""
    if not text or len(text) < min_phrase * 3:
        return text
    n = len(text)
    for phrase_len in range(min_phrase, n // 3 + 1):
        i = 0
        while i + phrase_len * 3 <= n:
            phrase = text[i:i + phrase_len]
            if (text[i + phrase_len:i + phrase_len * 2] == phrase
                    and text[i + phrase_len * 2:i + phrase_len * 3] == phrase):
                return text[:i + phrase_len].rstrip(', \n')
            i += 1
    return text


def _parse_llm_json(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # drop opening fence line (```json or ```)
        if lines and lines[0].strip().lstrip("`").strip() in ("json", ""):
            lines = lines[1:]
        # drop closing fence line
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    # Fallback: model hit token limit and truncated the JSON mid-string.
    # Extract whatever text was output before the cut-off.
    extracted = _extract_text_from_partial_json(stripped)
    if extracted:
        logger.warning(
            "LLM response truncated (token limit?); recovered %d chars of partial text", len(extracted)
        )
        return {"extracted_text": extracted, "_truncated": True}
    return {"parse_error": True, "raw_output": text}


def _call_openrouter(image_bgr: Any, page_label: str = "page_1", timeout_s: int = 120) -> Dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "").strip()
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    site_url = os.getenv("OPENROUTER_SITE_URL", "").strip()
    app_name = os.getenv("OPENROUTER_APP_NAME", "docuparse-ocr").strip()

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment")
    if not model:
        raise RuntimeError("OPENROUTER_MODEL not set in environment")

    instruction = (
        "Você é um OCR. Extraia fielmente todo o texto visível da imagem, preservando ordem de leitura. "
        "Retorne APENAS JSON válido com este schema: "
        '{"page":"string","extracted_text":"string","language":"string","confidence_0_1":"number",'
        '"key_values":[{"key":"string","value":"string"}]}. '
        "Se não houver texto, retorne extracted_text vazio e confidence_0_1 igual a 0."
    )

    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 8192,
        "frequency_penalty": 0.3,
        "messages": [
            {"role": "system", "content": "You are a precise OCR extraction engine."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction},
                    {"type": "text", "text": f"Identificador da página: {page_label}"},
                    {"type": "image_url", "image_url": {"url": _to_data_url(image_bgr)}},
                ],
            },
        ],
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if site_url:
        headers["HTTP-Referer"] = site_url
    if app_name:
        headers["X-Title"] = app_name

    logger.info("OpenRouter call | page=%s | model=%s", page_label, model)

    url = f"{base_url.rstrip('/')}/chat/completions"
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:400]}")

    body = resp.json()
    raw_content = body["choices"][0]["message"]["content"]
    logger.info("OpenRouter response | page=%s | preview=%.400s", page_label, raw_content)
    parsed = _parse_llm_json(raw_content)
    if parsed.get("parse_error"):
        logger.warning(
            "OpenRouter response could not be parsed as JSON | page=%s | raw=%.600s",
            page_label, raw_content,
        )
    else:
        extracted = parsed.get("extracted_text") or ""
        if extracted:
            cleaned = _remove_loop_repetitions(extracted)
            if cleaned != extracted:
                logger.info(
                    "OpenRouter loop removed | page=%s | before=%d chars | after=%d chars",
                    page_label, len(extracted), len(cleaned),
                )
                parsed["extracted_text"] = cleaned
    return parsed


# ── Engine class ─────────────────────────────────────────────────────────────

class OpenRouterOCREngine:
    """
    Primary OCR engine for the backend-ocr pipeline.

    Decision tree (mirrors ocr_openrouter_pipeline.py):
      PDF  + text layer  → Docling  (fallback: PyMuPDF)
      PDF  + image only  → render pages → OpenRouter vision
      Image file         → OpenRouter vision
    """

    def process(self, content: bytes, filename: str = "", timeout_s: int = 120) -> Dict[str, Any]:
        try:
            suffix = (filename or "").lower().rsplit(".", maxsplit=1)[-1] if "." in (filename or "") else ""
            is_pdf = suffix == "pdf" or content[:4] == b"%PDF"

            if is_pdf:
                return self._process_pdf(content, timeout_s=timeout_s)
            return self._process_image(content, timeout_s=timeout_s)

        except Exception as exc:
            logger.error("OpenRouterOCREngine error: %s", exc)
            return {
                "raw_text": "",
                "raw_text_fallback": f"Failed to process with openrouter: {exc}",
                "document_info": {},
                "entities": {},
                "tables": [],
                "totals": {},
                "_meta": {"engine": "openrouter", "error": str(exc)},
            }

    # ── PDF ──────────────────────────────────────────────────────────────────

    def _process_pdf(self, content: bytes, timeout_s: int = 120) -> Dict[str, Any]:
        pdf_class = _classify_pdf_bytes(content)
        logger.info("OpenRouter PDF classification: %s", pdf_class)

        if pdf_class["mode"] == "text":
            return self._process_text_pdf(content, pdf_class)

        return self._process_image_pdf(content, pdf_class, timeout_s=timeout_s)

    def _process_text_pdf(self, content: bytes, pdf_class: Dict[str, Any]) -> Dict[str, Any]:
        try:
            text = _extract_text_with_docling(content)
            engine_used = "docling"
        except Exception as exc:
            logger.warning("Docling failed (%s). Falling back to PyMuPDF.", exc)
            text = _extract_text_with_pymupdf(content)
            engine_used = "pymupdf"

        return {
            "raw_text": text,
            "raw_text_fallback": text,
            "document_info": {},
            "entities": {},
            "tables": [],
            "totals": {},
            "_meta": {
                "engine": engine_used,
                "pipeline": "text-extraction",
                "pdf_classification": pdf_class,
            },
        }

    def _process_image_pdf(self, content: bytes, pdf_class: Dict[str, Any], timeout_s: int = 120) -> Dict[str, Any]:
        images = _render_pdf_as_images(content, dpi=300)
        texts: List[str] = []
        page_results: List[Dict[str, Any]] = []
        page_errors: List[str] = []
        api_model = os.getenv("OPENROUTER_MODEL", "")

        for i, img in enumerate(images, start=1):
            label = f"page_{i}"
            try:
                result = _call_openrouter(img, page_label=label, timeout_s=timeout_s)
                if result.get("parse_error"):
                    err_msg = f"JSON parse error — raw: {str(result.get('raw_output', ''))[:300]}"
                    logger.warning("OpenRouter parse_error for %s: %s", label, err_msg)
                    page_errors.append(f"{label}: {err_msg}")
                    page_text = ""
                else:
                    page_text = result.get("extracted_text") or ""
                    if result.get("_truncated"):
                        logger.warning("OpenRouter %s: response was truncated — extracted %d chars (partial)", label, len(page_text))
                texts.append(page_text)
                page_results.append({
                    "page": label,
                    "text": page_text,
                    "confidence": result.get("confidence_0_1"),
                    **({"truncated": True} if result.get("_truncated") else {}),
                    **({"parse_error": result.get("raw_output", "")[:200]} if result.get("parse_error") else {}),
                })
                logger.info("OpenRouter %s: %d chars", label, len(page_text))
            except Exception as exc:
                logger.warning("OpenRouter failed for %s: %s", label, exc, exc_info=True)
                page_errors.append(f"{label}: {exc}")
                page_results.append({"page": label, "error": str(exc)})

        merged = "\n\n".join(t for t in texts if t).strip()
        confs = [r["confidence"] for r in page_results if isinstance(r.get("confidence"), (int, float))]
        avg_conf = round(sum(confs) / len(confs) * 100, 2) if confs else None

        if not merged and page_errors:
            fallback_msg = "OpenRouter errors: " + "; ".join(page_errors)
        else:
            fallback_msg = merged or "OpenRouter did not extract text from image PDF."

        return {
            "raw_text": merged,
            "raw_text_fallback": fallback_msg,
            "document_info": {},
            "entities": {},
            "tables": [],
            "totals": {},
            "_meta": {
                "engine": "openrouter",
                "model": api_model,
                "pipeline": "openrouter-ocr",
                "avg_confidence": avg_conf,
                "pdf_classification": pdf_class,
                "pages": page_results,
            },
        }

    # ── Image ─────────────────────────────────────────────────────────────────

    def _process_image(self, content: bytes, timeout_s: int = 120) -> Dict[str, Any]:
        nparr = np.frombuffer(content, np.uint8)
        image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image_bgr is None:
            raise RuntimeError("Could not decode image from bytes")

        api_model = os.getenv("OPENROUTER_MODEL", "")
        result = _call_openrouter(image_bgr, page_label="image_1", timeout_s=timeout_s)
        text = result.get("extracted_text") or ""
        confidence = result.get("confidence_0_1")
        avg_conf = round(confidence * 100, 2) if isinstance(confidence, (int, float)) else None

        return {
            "raw_text": text,
            "raw_text_fallback": text or "OpenRouter did not extract text from image.",
            "document_info": {},
            "entities": {},
            "tables": [],
            "totals": {},
            "_meta": {
                "engine": "openrouter",
                "model": api_model,
                "pipeline": "openrouter-ocr",
                "avg_confidence": avg_conf,
                "result": result,
            },
        }
