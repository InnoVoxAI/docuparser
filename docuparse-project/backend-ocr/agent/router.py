from typing import Dict, Any, List, Tuple
import time
import logging
import re
import unicodedata
import cv2
import numpy as np
import pytesseract

from agent.classifier import classify_document, get_engine_preprocessing_hints_for_class
from engines.deepseek_engine import DeepSeekEngine
from engines.docling_engine import DoclingEngine
from engines.easyocr_engine import EasyOCREngine
from engines.llamaparse_engine import LlamaParseEngine
from engines.paddle_engine import PaddleOCREngine
from engines.trocr_engine import TrOCREngine
from engines.tesseract_engine import TesseractEngine
from utils.preprocessing import (
    decode_image,
    encode_png_bytes,
    preprocess_for_deepseek_engine,
    preprocess_for_docling_engine,
    preprocess_for_easyocr_engine,
    preprocess_for_llamaparse_engine,
    preprocess_for_paddle_engine,
    preprocess_for_trocr_engine,
    segment_handwritten_regions,
    segment_text_lines,
)
from utils.validate_fields import (
    REQUIRED_FIELDS,
    compute_field_pipeline_quality,
    extract_dynamic_document_fields,
    extract_avg_confidence,
    merge_field_confidence,
    merge_fields_by_validation,
    resolve_field_fallback_engine,
)
from utils.ocr_fallback import (
    is_engine_error_fallback,
    merge_fallback_result,
    should_trigger_fallback,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Capabilities Dictionary
CAPABILITIES = {
    "digital_pdf": ["docling", "llamaparse"],
    "scanned_image": ["paddleocr", "easyocr"],
    "handwritten_complex": ["trocr", "paddleocr", "signature_tag", "easyocr"]
}



def _run_engine_by_name(
    engine_name: str,
    classification: str,
    content: bytes,
    filename: str,
) -> Dict[str, Any]:
    normalized_engine = engine_name.lower().strip()

    if normalized_engine == "tesseract":
        prepared_content, input_meta = _prepare_content_for_ocr(content, filename)
        engine = TesseractEngine()
        result = engine.process_with_classification(
            image_bytes=prepared_content,
            classification=classification,
        )
        result["input_meta"] = input_meta
        return result

    prepared_content, input_meta = _prepare_content_for_engine(
        content=content,
        filename=filename,
        classification=classification,
        engine_name=normalized_engine,
    )

    if normalized_engine == "easyocr":
        engine = EasyOCREngine()
        result = engine.process(prepared_content)
    elif normalized_engine == "paddle":
        engine = PaddleOCREngine()
        result = engine.process(prepared_content)
    elif normalized_engine == "deepseek":
        engine = DeepSeekEngine()
        if not engine.is_available():
            init_error = engine.get_init_error() or "unknown_error"
            raise RuntimeError(f"DeepSeek unavailable ({init_error})")
        result = engine.process(prepared_content)
    elif normalized_engine == "docling":
        engine = DoclingEngine()
        result = engine.process(prepared_content)
    elif normalized_engine == "llamaparse":
        engine = LlamaParseEngine()
        result = engine.process(prepared_content)
    elif normalized_engine == "trocr":
        result = _process_trocr_page(prepared_content, classification)
    else:
        raise ValueError(f"Unsupported fallback engine: {normalized_engine}")

    result["input_meta"] = input_meta
    return result


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
        if classification == "handwritten_complex":
            tools_used.extend(["region_segmentation", "paddleocr", "trocr"])
            data, input_meta = _process_handwritten_complex_by_regions(content=content, filename=filename)
            data["input_meta"] = input_meta
            _log_main_flow(
                classification=classification,
                selected_engine="handwritten_region_pipeline",
                input_meta=input_meta,
                default_preprocessing="region_segmentation_then_specialized_ocr",
            )

        elif resolved_engine == "tesseract":
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
            if should_trigger_fallback(data):
                logger.warning(
                    "PaddleOCR avg_confidence abaixo de 70%% (%.2f). Aplicando fallback TrOCR (prioritário).",
                    extract_avg_confidence(data),
                )
                try:
                    trocr_content, trocr_meta = _prepare_content_for_engine(
                        content=content,
                        filename=filename,
                        classification=classification,
                        engine_name="trocr",
                    )
                    _log_main_flow(
                        classification=classification,
                        selected_engine="trocr_fallback",
                        input_meta=trocr_meta,
                    )
                    fallback_data = _process_trocr_page(trocr_content, classification)
                    fallback_data["input_meta"] = input_meta
                    fallback_data["input_meta_fallback"] = trocr_meta
                    data = merge_fallback_result(data, fallback_data, primary_engine="paddleocr", fallback_engine="trocr")
                    tools_used.append("trocr_fallback")
                except Exception as trocr_fallback_err:
                    logger.warning(
                        "TrOCR fallback indisponível (%s). Aplicando fallback EasyOCR como contingência.",
                        str(trocr_fallback_err),
                    )
                    try:
                        fallback_engine = EasyOCREngine()
                        fallback_data = fallback_engine.process(prepared_content)
                        fallback_data["input_meta"] = input_meta
                        data = merge_fallback_result(data, fallback_data, primary_engine="paddleocr", fallback_engine="easyocr")
                        tools_used.append("easyocr_fallback_contingency")
                    except Exception as fallback_err:
                        tools_used.append("ocr_fallback_unavailable")
                        data["raw_text_fallback"] = (
                            "Fallback TrOCR indisponível; fallback EasyOCR também falhou: "
                            f"{str(fallback_err)}"
                        )

        elif resolved_engine in {"paddle_deepseek", "paddle_easyocr"}:
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
            # PaddleOCR handles printed content and EasyOCR is used as fallback.
            # TODO Verificar também se os campos críticos estão vazios, além da confiança, para acionar fallback.
            if should_trigger_fallback(paddle_data):
                logger.warning(
                    "PaddleOCR avg_confidence abaixo de 70%% (%.2f). Aplicando EasyOCR para conteúdo manuscrito/complexo.",
                    extract_avg_confidence(paddle_data),
                )
                tools_used.append("easyocr_hybrid_fallback")
                easyocr_content, easyocr_meta = _prepare_content_for_engine(
                    content=content,
                    filename=filename,
                    classification=classification,
                    engine_name="easyocr",
                )
                try:
                    _log_main_flow(
                        classification=classification,
                        selected_engine="easyocr_fallback",
                        input_meta=easyocr_meta,
                    )
                    easyocr_engine = EasyOCREngine()
                    easyocr_data = easyocr_engine.process(easyocr_content)
                    if is_engine_error_fallback(easyocr_data):
                        logger.warning("EasyOCR fallback returned engine error. Keeping PaddleOCR result.")
                        tools_used.append("easyocr_fallback_failed")
                        paddle_data.setdefault("_meta", {})
                        paddle_data["_meta"]["easyocr_fallback_error"] = (
                            easyocr_data.get("_meta", {}).get("error")
                            if isinstance(easyocr_data.get("_meta"), dict)
                            else "unknown_error"
                        )
                        data = paddle_data
                    else:
                        easyocr_meta = {**easyocr_meta, "triggered_by": "paddle_low_confidence"}
                        easyocr_data["input_meta"] = input_meta
                        easyocr_data["input_meta_fallback"] = easyocr_meta
                        data = merge_fallback_result(
                            paddle_data,
                            easyocr_data,
                            primary_engine="paddleocr",
                            fallback_engine="easyocr",
                        )
                except Exception as easyocr_error:
                    logger.warning(
                        "EasyOCR unavailable in hybrid flow (%s). Keeping PaddleOCR result.",
                        str(easyocr_error),
                    )
                    tools_used.append("easyocr_unavailable")
                    paddle_data.setdefault("_meta", {})
                    paddle_data["_meta"]["easyocr_unavailable_reason"] = str(easyocr_error)
                    paddle_data["raw_text_fallback"] = (
                        paddle_data.get("raw_text_fallback")
                        or f"EasyOCR indisponível no ambiente ({str(easyocr_error)}). Resultado mantido com PaddleOCR."
                    )
                    data = paddle_data
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
            if should_trigger_fallback(data):
                logger.warning(
                    "Docling avg_confidence abaixo de 70%% (%.2f). Aplicando fallback LlamaParse.",
                    extract_avg_confidence(data),
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
                data = merge_fallback_result(data, fallback_data, primary_engine="docling", fallback_engine="llamaparse")
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

        elif resolved_engine == "trocr":
            tools_used.append("trocr")
            prepared_content, input_meta = _prepare_content_for_ocr(content, filename)
            _log_main_flow(
                classification=classification,
                selected_engine=resolved_engine,
                input_meta=input_meta,
                default_preprocessing="trocr_region_pipeline",
            )
            data = _process_trocr_page(prepared_content, classification)
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

    field_quality = compute_field_pipeline_quality(data)
    field_quality["source"] = "primary"
    field_quality["fallback_engine"] = ""
    field_quality["fields_from_fallback"] = []

    logger.info(
        "FIELD_FALLBACK_CHECK | needed=%s | classification=%s | primary_engine=%s | final_score=%.4f",
        field_quality.get("fallback_needed"),
        classification,
        resolved_engine,
        float(field_quality.get("final_score", 0.0)),
    )

    if field_quality["fallback_needed"]:
        fallback_engine_name = resolve_field_fallback_engine(classification, resolved_engine)

        # TrOCR prioritário para documentos manuscritos complexos.
        if classification == "handwritten_complex" and fallback_engine_name in {None, "easyocr", "paddle"}:
            fallback_engine_name = "trocr"

        if fallback_engine_name:
            logger.info(
                "FIELD_FALLBACK_START | classification=%s | primary_engine=%s | fallback_engine=%s",
                classification,
                resolved_engine,
                fallback_engine_name,
            )
            try:
                fallback_data = _run_engine_by_name(
                    engine_name=fallback_engine_name,
                    classification=classification,
                    content=content,
                    filename=filename,
                )

                if not is_engine_error_fallback(fallback_data):
                    fallback_quality = compute_field_pipeline_quality(fallback_data)
                    merged_fields, fields_from_fallback = merge_fields_by_validation(
                        primary_fields=field_quality["fields"],
                        fallback_fields=fallback_quality["fields"],
                        fallback_validation=fallback_quality["validation"],
                    )

                    merged_confidence_pct = max(
                        (extract_avg_confidence(data) or 0.0),
                        (extract_avg_confidence(fallback_data) or 0.0),
                    )
                    merged_field_confidence = merge_field_confidence(
                        primary_confidence=field_quality.get("field_confidence", {}),
                        fallback_confidence=fallback_quality.get("field_confidence", {}),
                        fields_from_fallback=fields_from_fallback,
                    )

                    field_quality = compute_field_pipeline_quality(
                        data,
                        override_fields=merged_fields,
                        override_ocr_confidence=merged_confidence_pct,
                        override_field_confidence=merged_field_confidence,
                    )
                    field_quality["source"] = "fallback" if fields_from_fallback else "primary"
                    field_quality["fallback_engine"] = fallback_engine_name
                    field_quality["fields_from_fallback"] = fields_from_fallback

                    logger.info(
                        "FIELD_FALLBACK_RESULT | fallback_engine=%s | fields_from_fallback=%s | merged_final_score=%.4f | source=%s",
                        fallback_engine_name,
                        fields_from_fallback,
                        float(field_quality.get("final_score", 0.0)),
                        field_quality.get("source"),
                    )

                    if fields_from_fallback:
                        data = merge_fallback_result(
                            data,
                            fallback_data,
                            primary_engine=resolved_engine,
                            fallback_engine=fallback_engine_name,
                        )
                        tools_used.append(f"{fallback_engine_name}_field_fallback")
                else:
                    logger.warning(
                        "FIELD_FALLBACK_ENGINE_ERROR | fallback_engine=%s | reason=engine_error_payload",
                        fallback_engine_name,
                    )
                    field_quality["fallback_engine"] = fallback_engine_name
                    field_quality["source"] = "primary"
            except Exception as fallback_error:
                logger.warning(
                    "Field-driven fallback failed for engine %s: %s",
                    fallback_engine_name,
                    str(fallback_error),
                )
                field_quality["fallback_engine"] = fallback_engine_name
                field_quality["source"] = "primary"
                field_quality["fallback_error"] = str(fallback_error)
        else:
            logger.info(
                "FIELD_FALLBACK_SKIPPED | reason=no_engine_mapping | classification=%s | primary_engine=%s",
                classification,
                resolved_engine,
            )
    else:
        logger.info(
            "FIELD_FALLBACK_SKIPPED | reason=quality_ok | classification=%s | primary_engine=%s",
            classification,
            resolved_engine,
        )

    dynamic_fields = extract_dynamic_document_fields(
        data=data,
        base_fields=field_quality.get("fields", {}),
        classification=classification,
        engine_name=resolved_engine,
    )
    field_quality["dynamic_fields"] = dynamic_fields
    logger.info(
        "DYNAMIC_FIELDS | total=%d | classification=%s | engine=%s",
        len(dynamic_fields),
        classification,
        resolved_engine,
    )

    # Standardization
    normalized_data = _normalize_output(data, field_quality)

    try:
        field_positions_payload = _compute_field_positions(
            filename=filename,
            content=content,
            fields=normalized_data.get("fields", {}),
        )
    except Exception as field_position_error:
        logger.warning("Could not compute field positions: %s", str(field_position_error))
        field_positions_payload = {
            "field_positions": {},
            "field_positions_meta": {
                "available": False,
                "reason": str(field_position_error),
            },
        }

    normalized_data["field_positions"] = field_positions_payload.get("field_positions", {})
    normalized_data["field_positions_meta"] = field_positions_payload.get("field_positions_meta", {})

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
        "hybrid": "paddle_easyocr",
        "paddle_deepseek": "paddle_easyocr",
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
        return "handwritten_region"

    return "tesseract"


def _prepare_content_for_ocr(content: bytes, filename: str) -> Tuple[bytes, Dict[str, Any]]:
    suffix = filename.lower().rsplit(".", maxsplit=1)[-1] if "." in filename else ""

    # For image files we can process bytes directly.
    if suffix in {"jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp"}:
        return content, {
            "input_type": "image",
            "source_extension": f".{suffix}" if suffix else "",
            "rendered_from_pdf": False,
        }

    # For PDFs we render all pages as one stacked image before preprocessing/OCR.
    if suffix == "pdf":
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(content)
        if len(pdf) == 0:
            raise ValueError("PDF has no pages")

        page_images: List[np.ndarray] = []
        max_width = 0
        for page_idx in range(len(pdf)):
            page = pdf.get_page(page_idx)
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()
            image_rgb = np.array(pil_image)
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            page_images.append(image_bgr)
            max_width = max(max_width, image_bgr.shape[1])

        if not page_images:
            raise ValueError("PDF rendering returned no pages")

        separator_height = 24
        stacked_parts: List[np.ndarray] = []
        for page_idx, page_image in enumerate(page_images):
            height, width = page_image.shape[:2]
            if width < max_width:
                right_pad = np.full((height, max_width - width, 3), 255, dtype=np.uint8)
                page_image = np.concatenate([page_image, right_pad], axis=1)

            stacked_parts.append(page_image)
            if page_idx < len(page_images) - 1:
                separator = np.full((separator_height, max_width, 3), 255, dtype=np.uint8)
                stacked_parts.append(separator)

        stacked_image = np.concatenate(stacked_parts, axis=0)

        ok, encoded = cv2.imencode(".png", stacked_image)
        if not ok:
            raise ValueError("Could not convert PDF page to image bytes")

        return encoded.tobytes(), {
            "input_type": "pdf",
            "source_extension": ".pdf",
            "rendered_from_pdf": True,
            "rendered_page": "all",
            "stacked_pages": len(page_images),
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
    elif normalized_engine == "trocr":
        processed_content, preprocess_meta = preprocess_for_trocr_engine(base_content, classification=classification)
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


def _process_handwritten_complex_by_regions(content: bytes, filename: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    prepared_content, base_meta = _prepare_content_for_ocr(content, filename)
    image_bgr = decode_image(prepared_content)

    # PASSO CRÍTICO: segmenta e classifica regiões antes de executar OCR.
    regions = segment_handwritten_regions(image_bgr)

    paddle_engine = PaddleOCREngine()
    trocr_engine = TrOCREngine()

    merged_text_parts: List[str] = []
    region_outputs: List[Dict[str, Any]] = []
    region_confidences: List[float] = []

    for region in regions:
        region_type = str(region.get("type") or "printed").strip().lower()
        bbox = region.get("bbox") if isinstance(region.get("bbox"), dict) else {}
        region_image = region.get("image")

        if not isinstance(region_image, np.ndarray) or region_image.size == 0:
            continue

        text_output = ""
        used_engine = ""

        try:
            if region_type == "signature":
                text_output = "[ASSINATURA]"
                used_engine = "signature_tag"
                region_confidences.append(100.0)

            elif region_type == "handwritten":
                trocr_result = trocr_engine.process_region(region_image)
                text_output = str(trocr_result.get("text") or "").strip()
                used_engine = "trocr"
                region_confidences.append(90.0 if text_output else 0.0)

            else:
                region_bytes = encode_png_bytes(region_image)
                processed_bytes, _ = preprocess_for_paddle_engine(
                    region_bytes,
                    classification="scanned_image",
                )
                paddle_result = paddle_engine.process(processed_bytes)
                text_output = str(paddle_result.get("raw_text") or paddle_result.get("raw_text_fallback") or "").strip()
                used_engine = "paddleocr"
                region_meta = paddle_result.get("_meta") if isinstance(paddle_result.get("_meta"), dict) else {}
                region_confidences.append(float(region_meta.get("avg_confidence") or 0.0))

        except Exception as region_error:
            logger.warning(
                "Region OCR failed | type=%s | bbox=%s | reason=%s",
                region_type,
                bbox,
                str(region_error),
            )
            text_output = ""
            used_engine = f"{region_type}_error"
            region_confidences.append(0.0)

        if text_output:
            merged_text_parts.append(text_output)

        region_outputs.append(
            {
                "id": region.get("id"),
                "type": region_type,
                "bbox": bbox,
                "engine": used_engine,
                "text": text_output,
            }
        )

    merged_text = " ".join(part for part in merged_text_parts if part).strip()
    avg_confidence = float(np.mean(region_confidences)) if region_confidences else 0.0

    data: Dict[str, Any] = {
        "raw_text": merged_text,
        "raw_text_fallback": merged_text or "Pipeline regional para manuscrito não extraiu texto suficiente.",
        "document_info": {},
        "entities": {},
        "tables": [],
        "totals": {},
        "_meta": {
            "engine": "handwritten_region_pipeline",
            "avg_confidence": round(avg_confidence, 2),
            "fallback_recommended": avg_confidence < 70.0,
            "segmentation": {
                "total_regions": len(region_outputs),
                "printed_regions": sum(1 for item in region_outputs if item.get("type") == "printed"),
                "handwritten_regions": sum(1 for item in region_outputs if item.get("type") == "handwritten"),
                "signature_regions": sum(1 for item in region_outputs if item.get("type") == "signature"),
                "regions": region_outputs,
            },
        },
    }

    input_meta = {
        **base_meta,
        "engine_preprocessing": "handwritten_region_pipeline",
        "segmentation_enabled": True,
    }
    return data, input_meta


def _process_trocr_page(prepared_bytes: bytes, classification: str) -> Dict[str, Any]:
    """
    Full-page TrOCR: segments the image into regions, then into text lines,
    and runs TrOCR on each line crop. TrOCR is designed for single-line input —
    feeding it a full page produces garbage (hence the "0 1" symptom).
    """
    image_bgr = decode_image(prepared_bytes)
    regions = segment_handwritten_regions(image_bgr)

    trocr_engine = TrOCREngine()
    merged_text_parts: List[str] = []
    region_outputs: List[Dict[str, Any]] = []
    region_confidences: List[float] = []

    for region in regions:
        region_type = str(region.get("type") or "printed").strip().lower()
        bbox = region.get("bbox") if isinstance(region.get("bbox"), dict) else {}
        region_image = region.get("image")

        if not isinstance(region_image, np.ndarray) or region_image.size == 0:
            continue

        text_output = ""
        used_engine = "trocr"

        try:
            if region_type == "signature":
                text_output = "[ASSINATURA]"
                used_engine = "signature_tag"
                region_confidences.append(100.0)
            else:
                # Segment region into individual lines before feeding to TrOCR.
                line_crops = segment_text_lines(region_image)
                line_texts: List[str] = []
                for line_crop in line_crops:
                    line_result = trocr_engine.process_region(line_crop)
                    line_text = str(line_result.get("text") or "").strip()
                    if line_text:
                        line_texts.append(line_text)
                text_output = " ".join(line_texts).strip()
                region_confidences.append(90.0 if text_output else 0.0)
        except Exception as region_error:
            logger.warning(
                "TrOCR page region failed | type=%s | bbox=%s | reason=%s",
                region_type,
                bbox,
                str(region_error),
            )
            text_output = ""
            used_engine = f"{region_type}_error"
            region_confidences.append(0.0)

        if text_output:
            merged_text_parts.append(text_output)

        region_outputs.append({
            "id": region.get("id"),
            "type": region_type,
            "bbox": bbox,
            "engine": used_engine,
            "text": text_output,
        })

    merged_text = " ".join(part for part in merged_text_parts if part).strip()
    avg_confidence = float(np.mean(region_confidences)) if region_confidences else 0.0

    return {
        "raw_text": merged_text,
        "raw_text_fallback": merged_text or "TrOCR não extraiu texto suficiente da imagem.",
        "document_info": {},
        "entities": {},
        "tables": [],
        "totals": {},
        "_meta": {
            "engine": "trocr",
            "avg_confidence": round(avg_confidence, 2),
            "fallback_recommended": avg_confidence < 70.0,
            "segmentation": {
                "total_regions": len(region_outputs),
                "regions": region_outputs,
            },
        },
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


def _normalize_output(data: Dict[str, Any], field_quality: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Ensures the output follows the strict JSON schema.
    """
    field_quality = field_quality or {}
    dynamic_fields = field_quality.get("dynamic_fields") if isinstance(field_quality.get("dynamic_fields"), dict) else {}
    if dynamic_fields:
        normalized_fields = {
            str(field_name).strip(): str(field_value or "").strip()
            for field_name, field_value in dynamic_fields.items()
            if str(field_name or "").strip() and str(field_value or "").strip()
        }
    else:
        fields = field_quality.get("fields") if isinstance(field_quality.get("fields"), dict) else {}
        normalized_fields = {
            field_name: str(fields.get(field_name) or "").strip()
            for field_name in [*REQUIRED_FIELDS, "cnpj_tomador"]
        }

    return {
        "fields": normalized_fields,
        "required_fields": REQUIRED_FIELDS,
        "field_validation": field_quality.get("validation", {}),
        "field_confidence": field_quality.get("field_confidence", {}),
        "low_confidence_fields": field_quality.get("low_confidence_fields", []),
        "field_score": field_quality.get("field_score", 0.0),
        "ocr_confidence": field_quality.get("ocr_confidence", 0.0),
        "final_score": field_quality.get("final_score", 0.0),
        "fallback_needed": field_quality.get("fallback_needed", False),
        "source": field_quality.get("source", "primary"),
        "fallback_engine": field_quality.get("fallback_engine", ""),
        "fields_from_fallback": field_quality.get("fields_from_fallback", []),
        "totals": data.get("totals", {}),
        "raw_text": data.get("raw_text") or data.get("raw_text_fallback", ""),
        "raw_text_fallback": data.get("raw_text_fallback", ""),
        "ocr_meta": data.get("_meta", {}),
    }


def _normalize_text_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFD", str(value or "").lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _tokenize_for_match(value: str) -> List[str]:
    return [token for token in _normalize_text_for_match(value).split() if len(token) >= 2]


def _extract_layout_tokens(image_bytes: bytes) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise ValueError("Could not decode image to extract field positions")

    image_height, image_width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    data = pytesseract.image_to_data(gray, lang="por+eng", config="--oem 3 --psm 6", output_type=pytesseract.Output.DICT)

    tokens: List[Dict[str, Any]] = []
    size = len(data.get("text", []))
    for idx in range(size):
        text = str(data.get("text", [""])[idx] or "").strip()
        if not text:
            continue

        try:
            confidence = float(data.get("conf", ["-1"])[idx])
        except (TypeError, ValueError):
            confidence = -1.0

        if confidence < 0:
            continue

        left = int(data.get("left", [0])[idx] or 0)
        top = int(data.get("top", [0])[idx] or 0)
        width = int(data.get("width", [0])[idx] or 0)
        height = int(data.get("height", [0])[idx] or 0)

        if width <= 0 or height <= 0:
            continue

        normalized_text = _normalize_text_for_match(text)
        if not normalized_text:
            continue

        tokens.append({
            "index": idx,
            "text": text,
            "norm": normalized_text,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "confidence": confidence,
        })

    metadata = {
        "image_width": image_width,
        "image_height": image_height,
        "token_count": len(tokens),
    }
    return tokens, metadata


def _build_bbox_from_tokens(tokens: List[Dict[str, Any]], image_width: int, image_height: int) -> Dict[str, Any]:
    min_left = min(token["left"] for token in tokens)
    min_top = min(token["top"] for token in tokens)
    max_right = max(token["left"] + token["width"] for token in tokens)
    max_bottom = max(token["top"] + token["height"] for token in tokens)

    width = max_right - min_left
    height = max_bottom - min_top

    safe_width = max(image_width, 1)
    safe_height = max(image_height, 1)

    return {
        "x": min_left,
        "y": min_top,
        "width": width,
        "height": height,
        "normalized_bbox": {
            "x": round(min_left / safe_width, 6),
            "y": round(min_top / safe_height, 6),
            "width": round(width / safe_width, 6),
            "height": round(height / safe_height, 6),
        },
    }


def _match_field_tokens(field_value: str, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized_value = _normalize_text_for_match(field_value)
    if not normalized_value:
        return []

    value_tokens = _tokenize_for_match(field_value)
    if not value_tokens:
        return []

    max_window = max(2, min(len(value_tokens) + 3, 10))
    best_span: List[Dict[str, Any]] = []
    best_score = -1.0

    for start_idx in range(len(tokens)):
        window = tokens[start_idx:start_idx + max_window]
        if not window:
            continue

        matched = [token for token in window if token["norm"] in normalized_value or normalized_value in token["norm"]]
        if not matched:
            continue

        covered_chars = sum(len(token["norm"]) for token in matched)
        proximity_penalty = (matched[-1]["index"] - matched[0]["index"]) * 0.02
        score = covered_chars - proximity_penalty

        if score > best_score:
            best_score = score
            best_span = matched

    if best_span:
        return best_span

    fallback_matches = [token for token in tokens if token["norm"] in normalized_value or normalized_value in token["norm"]]
    if fallback_matches:
        fallback_matches.sort(key=lambda token: len(token["norm"]), reverse=True)
        return [fallback_matches[0]]

    return []


def _compute_field_positions(filename: str, content: bytes, fields: Dict[str, str]) -> Dict[str, Any]:
    if not isinstance(fields, dict) or not fields:
        return {
            "field_positions": {},
            "field_positions_meta": {
                "available": False,
                "reason": "no_fields",
            },
        }

    rendered_image_bytes, input_meta = _prepare_content_for_ocr(content, filename)
    tokens, layout_meta = _extract_layout_tokens(rendered_image_bytes)

    if not tokens:
        return {
            "field_positions": {},
            "field_positions_meta": {
                "available": False,
                "reason": "no_layout_tokens",
                "input_meta": input_meta,
                **layout_meta,
            },
        }

    image_width = layout_meta["image_width"]
    image_height = layout_meta["image_height"]

    field_positions: Dict[str, Any] = {}
    for field_name, field_value in fields.items():
        value_text = str(field_value or "").strip()
        if not value_text:
            continue

        matched_tokens = _match_field_tokens(value_text, tokens)
        if not matched_tokens:
            continue

        bbox = _build_bbox_from_tokens(matched_tokens, image_width, image_height)
        field_positions[field_name] = {
            "bbox": {
                "x": bbox["x"],
                "y": bbox["y"],
                "width": bbox["width"],
                "height": bbox["height"],
            },
            "normalized_bbox": bbox["normalized_bbox"],
            "page": 1,
            "matched_text": " ".join(token["text"] for token in matched_tokens).strip(),
            "confidence": round(sum(token["confidence"] for token in matched_tokens) / len(matched_tokens), 2),
        }

    return {
        "field_positions": field_positions,
        "field_positions_meta": {
            "available": bool(field_positions),
            "input_meta": input_meta,
            **layout_meta,
            "coordinates_basis": "rendered_input_image",
            "coordinate_space": "pixels_and_normalized",
        },
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
