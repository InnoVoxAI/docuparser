from typing import Dict, Any, List, Tuple
import time
import logging
import cv2
import numpy as np
import pytesseract

from agent.classifier import classify_document, get_engine_preprocessing_hints_for_class
from engines.deepseek_engine import DeepSeekEngine
from engines.docling_engine import DoclingEngine
from engines.easyocr_engine import EasyOCREngine
from engines.llamaparse_engine import LlamaParseEngine
from engines.paddle_engine import PaddleOCREngine
from engines.tesseract_engine import TesseractEngine
from utils.preprocessing import (
    preprocess_for_deepseek_engine,
    preprocess_for_docling_engine,
    preprocess_for_easyocr_engine,
    preprocess_for_llamaparse_engine,
    preprocess_for_paddle_engine,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Capabilities Dictionary
CAPABILITIES = {
    "digital_pdf": ["docling", "llamaparse"],
    "scanned_image": ["paddleocr", "easyocr"],
    "handwritten_complex": ["paddleocr", "deepseek-ocr"]
}


def route_and_process(filename: str, content: bytes, selected_engine: str | None = None) -> Dict[str, Any]:
    """
    Selects the tool/engine based on classification and processes the content.
    """
    start_time = time.perf_counter()
    tools_used: List[str] = []
    data: Dict[str, Any] = {}
    classification = classify_document(filename, content)
    logger.info(f"--- Document classified as: {classification}")
    resolved_engine = _resolve_engine(classification, selected_engine)
    logger.info("--- Engine selected: %s", resolved_engine)

    try:
        if resolved_engine == "tesseract":
            tools_used.append("pytesseract")
            prepared_content, input_meta = _prepare_content_for_ocr(content, filename)
            _log_main_flow(
                classification=classification,
                selected_engine=resolved_engine,
                input_meta=input_meta,
                default_preprocessing="tesseract_classification_default",
            )
            engine = TesseractEngine()
            data = engine.process_with_classification(
                image_bytes=prepared_content,
                classification=classification,
            )
            data["input_meta"] = input_meta

        elif resolved_engine == "easyocr":
            prepared_content, input_meta = _prepare_content_for_engine(
                content=content,
                filename=filename,
                classification=classification,
                engine_name="easyocr",
            )
            _log_main_flow(
                classification=classification,
                selected_engine=resolved_engine,
                input_meta=input_meta,
            )
            try:
                from engines.easyocr_engine import EasyOCREngine

                tools_used.append("easyocr")
                engine = EasyOCREngine()
                data = engine.process(prepared_content)
                data["input_meta"] = input_meta
            except (ModuleNotFoundError, RuntimeError) as import_err:
                logger.warning(
                    "EasyOCR unavailable (%s). Falling back to Tesseract.",
                    str(import_err),
                )
                tools_used.extend(["easyocr_unavailable", "pytesseract_fallback"])
                engine = TesseractEngine()
                data = engine.process_with_classification(
                    image_bytes=prepared_content,
                    classification=classification,
                )
                data["input_meta"] = input_meta
                data["raw_text_fallback"] = "EasyOCR indisponível no ambiente; fallback para Tesseract aplicado."

        elif resolved_engine == "paddle":
            tools_used.append("paddleocr")
            prepared_content, input_meta = _prepare_content_for_engine(
                content=content,
                filename=filename,
                classification=classification,
                engine_name="paddle",
            )
            _log_main_flow(
                classification=classification,
                selected_engine=resolved_engine,
                input_meta=input_meta,
            )
            engine = PaddleOCREngine()
            data = engine.process(prepared_content)
            data["input_meta"] = input_meta

            # TODO Verificar também se os campos críticos estão vazios, além da confiança, para acionar fallback.
            if _should_trigger_fallback(data):
                logger.warning(
                    "PaddleOCR avg_confidence abaixo de 70%% (%.2f). Aplicando fallback EasyOCR.",
                    _extract_avg_confidence(data),
                )
                try:
                    fallback_engine = EasyOCREngine()
                    fallback_data = fallback_engine.process(prepared_content)
                    fallback_data["input_meta"] = input_meta
                    data = _merge_fallback_result(data, fallback_data, primary_engine="paddleocr", fallback_engine="easyocr")
                    tools_used.append("easyocr_fallback")
                except Exception as fallback_err:
                    tools_used.append("easyocr_fallback_unavailable")
                    data["raw_text_fallback"] = (
                        f"Fallback EasyOCR indisponível: {str(fallback_err)}"
                    )

        elif resolved_engine == "paddle_deepseek":
            tools_used.append("paddleocr")
            prepared_content, input_meta = _prepare_content_for_engine(
                content=content,
                filename=filename,
                classification=classification,
                engine_name="paddle",
            )
            _log_main_flow(
                classification=classification,
                selected_engine=resolved_engine,
                input_meta=input_meta,
            )
            paddle_engine = PaddleOCREngine()
            paddle_data = paddle_engine.process(prepared_content)
            paddle_data["input_meta"] = input_meta

            # Hybrid approach for handwritten/complex docs:
            # PaddleOCR handles printed content, DeepSeek is activated as fallback
            # only when avg_confidence is below threshold.
            # TODO Verificar também se os campos críticos estão vazios, além da confiança, para acionar fallback.
            if _should_trigger_fallback(paddle_data):
                logger.warning(
                    "PaddleOCR avg_confidence abaixo de 70%% (%.2f). Aplicando DeepSeek para conteúdo manuscrito/complexo.",
                    _extract_avg_confidence(paddle_data),
                )
                tools_used.append("deepseek_hybrid_fallback")
                deepseek_engine = DeepSeekEngine()
                deepseek_content, deepseek_meta = _prepare_content_for_engine(
                    content=content,
                    filename=filename,
                    classification=classification,
                    engine_name="deepseek",
                )
                if not deepseek_engine.is_available():
                    deepseek_reason = deepseek_engine.get_init_error() or "unknown_error"
                    logger.warning(
                        "DeepSeek unavailable in hybrid flow (%s). Keeping PaddleOCR result.",
                        deepseek_reason,
                    )
                    tools_used.append("deepseek_unavailable")
                    paddle_data.setdefault("_meta", {})
                    paddle_data["_meta"]["deepseek_unavailable_reason"] = deepseek_reason
                    paddle_data["raw_text_fallback"] = (
                        paddle_data.get("raw_text_fallback")
                        or f"DeepSeek indisponível no ambiente ({deepseek_reason}). Resultado mantido com PaddleOCR."
                    )
                    data = paddle_data
                else:
                    _log_main_flow(
                        classification=classification,
                        selected_engine="deepseek_fallback",
                        input_meta=deepseek_meta,
                    )
                    deepseek_data = deepseek_engine.process(deepseek_content)
                    if _is_engine_error_fallback(deepseek_data):
                        logger.warning("DeepSeek fallback returned engine error. Keeping PaddleOCR result.")
                        tools_used.append("deepseek_fallback_failed")
                        paddle_data.setdefault("_meta", {})
                        paddle_data["_meta"]["deepseek_fallback_error"] = (
                            deepseek_data.get("_meta", {}).get("error")
                            if isinstance(deepseek_data.get("_meta"), dict)
                            else "unknown_error"
                        )
                        data = paddle_data
                    else:
                        deepseek_meta = {**deepseek_meta, "triggered_by": "paddle_low_confidence"}
                        deepseek_data["input_meta"] = input_meta
                        deepseek_data["input_meta_fallback"] = deepseek_meta
                        data = _merge_fallback_result(
                            paddle_data,
                            deepseek_data,
                            primary_engine="paddleocr",
                            fallback_engine="deepseek-ocr",
                        )
            else:
                data = paddle_data

        elif resolved_engine == "deepseek":
            tools_used.append("deepseek-ocr")
            logger.warning("######### deepseek selecionado!")
            engine = DeepSeekEngine()
            prepared_content, input_meta = _prepare_content_for_engine(
                content=content,
                filename=filename,
                classification=classification,
                engine_name="deepseek",
            )
            _log_main_flow(
                classification=classification,
                selected_engine=resolved_engine,
                input_meta=input_meta,
            )
            if not engine.is_available():
                init_error = engine.get_init_error() or "unknown_error"
                logger.warning(
                    "DeepSeek unavailable (%s). Falling back to Tesseract.",
                    init_error,
                )
                tools_used.extend(["deepseek_unavailable", "pytesseract_fallback"])
                fallback_engine = TesseractEngine()
                data = fallback_engine.process_with_classification(
                    image_bytes=prepared_content,
                    classification=classification,
                )
                data["input_meta"] = input_meta
                data["raw_text_fallback"] = (
                    f"DeepSeek indisponível no ambiente ({init_error}). Fallback para Tesseract aplicado."
                )
            else:
                data = engine.process(prepared_content)
                data["input_meta"] = input_meta

        elif resolved_engine == "docling":
            tools_used.append("docling")
            engine = DoclingEngine()
            prepared_content, input_meta = _prepare_content_for_engine(
                content=content,
                filename=filename,
                classification=classification,
                engine_name="docling",
            )
            _log_main_flow(
                classification=classification,
                selected_engine=resolved_engine,
                input_meta=input_meta,
            )
            data = engine.process(prepared_content)
            data["input_meta"] = input_meta

            # TODO Verificar também se os campos críticos estão vazios, além da confiança, para acionar fallback.
            if _should_trigger_fallback(data):
                logger.warning(
                    "Docling avg_confidence abaixo de 70%% (%.2f). Aplicando fallback LlamaParse.",
                    _extract_avg_confidence(data),
                )
                fallback_engine = LlamaParseEngine()
                fallback_content, fallback_meta = _prepare_content_for_engine(
                    content=content,
                    filename=filename,
                    classification=classification,
                    engine_name="llamaparse",
                )
                _log_main_flow(
                    classification=classification,
                    selected_engine="llamaparse_fallback",
                    input_meta=fallback_meta,
                )
                fallback_data = fallback_engine.process(fallback_content)
                fallback_data["input_meta"] = fallback_meta
                data = _merge_fallback_result(data, fallback_data, primary_engine="docling", fallback_engine="llamaparse")
                tools_used.append("llamaparse_fallback")

        elif resolved_engine == "llamaparse":
            tools_used.append("llamaparse")
            engine = LlamaParseEngine()
            prepared_content, input_meta = _prepare_content_for_engine(
                content=content,
                filename=filename,
                classification=classification,
                engine_name="llamaparse",
            )
            _log_main_flow(
                classification=classification,
                selected_engine=resolved_engine,
                input_meta=input_meta,
            )
            data = engine.process(prepared_content)
            data["input_meta"] = input_meta

        else:
            tools_used.append("basic_fallback")
            data = _mock_extract(content)

    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract binary is not installed or not available in PATH")
        tools_used.append("tesseract_unavailable")
        data = _mock_extract(content)
        data["raw_text_fallback"] = (
            "Tesseract não está instalado no sistema (binário ausente no PATH). "
            "Instale o pacote 'tesseract-ocr' e reinicie o serviço backend-ocr."
        )
    except (FileNotFoundError, OSError) as os_err:
        logger.error("OCR runtime error: %s", str(os_err))
        tools_used.append("ocr_runtime_error")
        data = _mock_extract(content)
        data["raw_text_fallback"] = f"OCR indisponível no ambiente: {str(os_err)}"
    except Exception as e:
        logger.error(f"Routing error: {e}")
        tools_used.append("processing_error")
        data = _mock_extract(content)
        data["raw_text_fallback"] = f"Processing Error: {str(e)}"

    end_time = time.perf_counter()
    processing_time = (end_time - start_time) * 1000

    logger.info(f"Processed {classification} in {processing_time:.2f}ms using {tools_used}")

    # Standardization
    normalized_data = _normalize_output(data)

    return {
        "classification": classification,
        "selected_engine": resolved_engine,
        "tools_used": tools_used,
        "transcription": normalized_data,
    }


def _resolve_engine(classification: str, selected_engine: str | None) -> str:
    aliases = {
        "paddleocr": "paddle",
        "paddle_ocr": "paddle",
        "llama-parse": "llamaparse",
        "deepseek-ocr": "deepseek",
        "hybrid": "paddle_deepseek",
    }

    if selected_engine:
        normalized_engine = selected_engine.lower().strip()
        normalized_engine = aliases.get(normalized_engine, normalized_engine)
        if normalized_engine not in {"", "none", "null"}:
            return normalized_engine

    if classification == "digital_pdf":
        return "docling"

    if classification == "scanned_image":
        return "paddle"

    if classification == "handwritten_complex":
        return "paddle_deepseek"

    return "tesseract"


def _extract_avg_confidence(data: Dict[str, Any]) -> float | None:
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


def _should_trigger_fallback(data: Dict[str, Any], min_confidence: float = 70.0) -> bool:
    avg_confidence = _extract_avg_confidence(data)
    return avg_confidence is not None and avg_confidence < min_confidence


def _is_engine_error_fallback(data: Dict[str, Any]) -> bool:
    if not isinstance(data, dict):
        return True

    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    if meta.get("error"):
        return True

    raw_text_fallback = str(data.get("raw_text_fallback", "") or "")
    return raw_text_fallback.startswith("Failed to process with")


def _merge_fallback_result(
    primary_data: Dict[str, Any],
    fallback_data: Dict[str, Any],
    primary_engine: str,
    fallback_engine: str,
) -> Dict[str, Any]:
    """
    Combina o resultado do OCR primário com o resultado do fallback.

    Objetivo:
    - preservar tudo que já veio do engine primário;
    - sobrescrever apenas campos úteis quando o fallback trouxer valor real;
    - registrar no _meta que houve fallback e qual engine foi usado.
    """
    # Começa com uma cópia do resultado primário para manter o baseline.
    merged = dict(primary_data)

    # Atualiza apenas os campos principais quando o fallback trouxer conteúdo não vazio.
    for key in ["document_info", "entities", "tables", "totals", "raw_text", "raw_text_fallback"]:
        fallback_value = fallback_data.get(key)
        if fallback_value not in (None, "", [], {}):
            merged[key] = fallback_value

    # Lê metadados de ambos os resultados de forma segura.
    primary_meta = primary_data.get("_meta") if isinstance(primary_data.get("_meta"), dict) else {}
    fallback_meta = fallback_data.get("_meta") if isinstance(fallback_data.get("_meta"), dict) else {}

    # Consolida metadados e marca explicitamente o contexto do fallback.
    merged["_meta"] = {
        **primary_meta,
        **fallback_meta,
        "primary_engine": primary_engine,
        "fallback_engine": fallback_engine,
        "primary_avg_confidence": _extract_avg_confidence(primary_data),
        "fallback_triggered": True,
    }

    return merged


def _prepare_content_for_ocr(content: bytes, filename: str) -> Tuple[bytes, Dict[str, Any]]:
    suffix = filename.lower().rsplit(".", maxsplit=1)[-1] if "." in filename else ""

    # For image files we can process bytes directly.
    if suffix in {"jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp"}:
        return content, {
            "input_type": "image",
            "source_extension": f".{suffix}" if suffix else "",
            "rendered_from_pdf": False,
        }

    # For PDFs we render the first page as PNG before preprocessing/OCR.
    if suffix == "pdf":
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(content)
        if len(pdf) == 0:
            raise ValueError("PDF has no pages")

        page = pdf.get_page(0)
        bitmap = page.render(scale=2.0)
        pil_image = bitmap.to_pil()

        image_rgb = np.array(pil_image)
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        ok, encoded = cv2.imencode(".png", image_bgr)
        if not ok:
            raise ValueError("Could not convert PDF page to image bytes")

        return encoded.tobytes(), {
            "input_type": "pdf",
            "source_extension": ".pdf",
            "rendered_from_pdf": True,
            "rendered_page": 1,
            "pdf_page_count": len(pdf),
        }

    raise ValueError("Unsupported file extension. Use PDF or an image file")


def _prepare_content_for_engine(
    content: bytes,
    filename: str,
    classification: str,
    engine_name: str,
) -> Tuple[bytes, Dict[str, Any]]:
    suffix = filename.lower().rsplit(".", maxsplit=1)[-1] if "." in filename else ""
    normalized_engine = engine_name.lower().strip()

    classification_hints = get_engine_preprocessing_hints_for_class(classification)

    if normalized_engine in {"docling", "llamaparse"} and suffix == "pdf":
        parser_meta = _build_pdf_parser_meta(content=content, engine_name=normalized_engine)
        parser_meta["classification_preprocessing_hints"] = classification_hints
        return content, parser_meta

    base_content, base_meta = _prepare_content_for_ocr(content, filename)

    if normalized_engine == "paddle":
        processed_content, preprocess_meta = preprocess_for_paddle_engine(base_content, classification=classification)
    elif normalized_engine == "easyocr":
        processed_content, preprocess_meta = preprocess_for_easyocr_engine(base_content, classification=classification)
    elif normalized_engine == "deepseek":
        processed_content, preprocess_meta = preprocess_for_deepseek_engine(base_content, classification=classification)
    elif normalized_engine == "docling":
        processed_content, preprocess_meta = preprocess_for_docling_engine(base_content, classification=classification)
    elif normalized_engine == "llamaparse":
        processed_content, preprocess_meta = preprocess_for_llamaparse_engine(base_content, classification=classification)
    else:
        return base_content, {
            **base_meta,
            "classification_preprocessing_hints": classification_hints,
        }

    return processed_content, {
        **base_meta,
        **preprocess_meta,
        "classification_preprocessing_hints": classification_hints,
    }


def _build_pdf_parser_meta(content: bytes, engine_name: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "input_type": "pdf",
        "source_extension": ".pdf",
        "prefer_original_pdf": True,
        "engine_preprocessing": f"{engine_name}_pdf_native",
    }

    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(content)
        page_count = len(pdf)
        non_empty_pages = 0
        sampled_pages = min(page_count, 3)

        for page_idx in range(sampled_pages):
            page = pdf.get_page(page_idx)
            text_page = page.get_textpage()
            text = text_page.get_text_bounded() or ""
            if text.strip():
                non_empty_pages += 1

        meta["pdf_page_count"] = page_count
        meta["sampled_text_pages"] = sampled_pages
        meta["non_empty_text_pages"] = non_empty_pages
    except Exception as exc:
        meta["pdf_validation_error"] = str(exc)

    return meta


def _log_main_flow(
    classification: str,
    selected_engine: str,
    input_meta: Dict[str, Any] | None = None,
    default_preprocessing: str = "not_informed",
) -> None:
    preprocessing = default_preprocessing
    if isinstance(input_meta, dict):
        preprocessing = input_meta.get("engine_preprocessing") or preprocessing

    logger.info(
        "FLOW_TEST_LOG | classification=%s | engine=%s | preprocessing=%s",
        classification,
        selected_engine,
        preprocessing,
    )


def _normalize_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures the output follows the strict JSON schema.
    """
    return {
        "document_info": data.get("document_info", {}),
        "entities": data.get("entities", {}),
        "tables": data.get("tables", []),  # Ensure lists
        "totals": data.get("totals", {}),
        "raw_text": data.get("raw_text") or data.get("raw_text_fallback", ""),
        "raw_text_fallback": data.get("raw_text_fallback", ""),
        "ocr_meta": data.get("_meta", {}),
    }


def _mock_extract(content: bytes) -> Dict[str, Any]:
    return {
        "document_info": {},
        "entities": {},
        "tables": [],
        "totals": {},
        "raw_text": "",
        "raw_text_fallback": "Content processed (mock)"
    }
