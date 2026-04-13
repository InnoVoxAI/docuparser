from typing import Dict, Any, List, Tuple
import time
import logging
import cv2
import numpy as np
import pytesseract

from agent.classifier import classify_document
from engines.deepseek_engine import DeepSeekEngine
from engines.docling_engine import DoclingEngine
from engines.llamaparse_engine import LlamaParseEngine
from engines.tesseract_engine import TesseractEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Capabilities Dictionary
CAPABILITIES = {
    "digital_pdf": ["pdfplumber", "docling"],
    "scanned_image": ["opencv-python", "pytesseract", "easyocr"],
    "handwritten_complex": ["deepseek-ocr", "llama-parse", "unstructured"]
}


def route_and_process(filename: str, content: bytes, selected_engine: str | None = None) -> Dict[str, Any]:
    """
    Selects the tool/engine based on classification and processes the content.
    """
    start_time = time.perf_counter()
    tools_used: List[str] = []
    data: Dict[str, Any] = {}
    classification = classify_document(filename, content)
    resolved_engine = _resolve_engine(classification, selected_engine)

    try:
        if resolved_engine == "tesseract":
            tools_used.append("pytesseract")
            prepared_content, input_meta = _prepare_content_for_ocr(content, filename)
            engine = TesseractEngine()
            data = engine.process_with_classification(
                image_bytes=prepared_content,
                classification=classification,
            )
            data["input_meta"] = input_meta

        elif resolved_engine == "easyocr":
            prepared_content, input_meta = _prepare_content_for_ocr(content, filename)
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

        elif resolved_engine == "deepseek":
            tools_used.append("deepseek-ocr")
            engine = DeepSeekEngine()
            data = engine.process(content)

        elif resolved_engine == "docling":
            tools_used.append("docling")
            engine = DoclingEngine()
            data = engine.process(content)

        elif resolved_engine == "llamaparse":
            tools_used.append("llamaparse")
            engine = LlamaParseEngine()
            data = engine.process(content)

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
    if selected_engine:
        return selected_engine.lower().strip()

    if classification in {"digital_pdf", "scanned_image"}:
        return "tesseract"

    if classification == "handwritten_complex":
        return "deepseek"

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
