# =============================================================================
# INFRASTRUCTURE: infrastructure/engines/tesseract_engine.py
# =============================================================================
# Engine OCR local via pytesseract.
#
# Origem: migrado de engines/tesseract_engine.py (Fase 4 do refactor).
# engines/tesseract_engine.py agora é shim que re-exporta desta localização.
#
# Mudanças em relação ao original:
#   - Herda de BaseOCREngine (contrato comum)
#   - Propriedade name adicionada
#   - process() aceita metadata (parâmetro opcional ignorado por este engine)
#   - Importa de shared.preprocessing em vez de utils.preprocessing
# =============================================================================

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

import cv2
import fitz
import numpy as np
import pytesseract
from pytesseract import Output

from infrastructure.engines.base_engine import BaseOCREngine
from shared.preprocessing import preprocess_image


class TesseractEngine(BaseOCREngine):

    @property
    def name(self) -> str:
        return "tesseract"

    @staticmethod
    def _format_seconds(seconds_value: float) -> str:
        return f"({seconds_value:.1f}s)"

    def _decode_to_gray(self, image_data: Any) -> np.ndarray:
        if isinstance(image_data, np.ndarray):
            image = image_data
        else:
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None or image.size == 0:
            raise ValueError("Could not decode image for Tesseract OCR")

        if len(image.shape) == 2:
            return image

        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def _build_variants(self, gray: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        resized = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        blur = cv2.GaussianBlur(resized, (3, 3), 0)
        otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        adaptive = cv2.adaptiveThreshold(
            blur,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )
        inverted = cv2.bitwise_not(adaptive)

        return [
            ("gray_resized", resized),
            ("otsu", otsu),
            ("adaptive", adaptive),
            ("adaptive_inverted", inverted),
        ]

    def _extract_with_data(self, image: np.ndarray, lang: str, psm: int) -> Tuple[str, float]:
        config = f"--oem 3 --psm {psm}"
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            config=config,
            output_type=Output.DICT,
        )

        words = []
        confidences = []
        for text, conf in zip(data.get("text", []), data.get("conf", [])):
            normalized = str(text).strip()
            if not normalized:
                continue

            try:
                conf_value = float(conf)
            except (TypeError, ValueError):
                continue

            if conf_value < 0:
                continue

            words.append(normalized)
            confidences.append(conf_value)

        extracted_text = " ".join(words).strip()
        avg_conf = float(np.mean(confidences)) if confidences else 0.0
        return extracted_text, avg_conf

    def _build_term_metrics(self, image: np.ndarray, lang: str, psm: int, total_seconds: float) -> Dict[str, Any]:
        config = f"--oem 3 --psm {psm}"
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            config=config,
            output_type=Output.DICT,
        )

        terms = []
        for text, conf in zip(data.get("text", []), data.get("conf", [])):
            normalized = str(text).strip()
            if not normalized:
                continue

            try:
                conf_value = float(conf)
            except (TypeError, ValueError):
                continue

            if conf_value < 0:
                continue

            terms.append((normalized, conf_value))

        if not terms:
            return {
                "confidence_by_term": {},
                "conversion_time_by_term": {},
                "total_conversion_time": self._format_seconds(total_seconds),
            }

        total_weight = sum(max(len(term), 1) for term, _ in terms)
        confidence_by_term: Dict[str, List[float]] = {}
        conversion_time_by_term: Dict[str, str] = {}

        for index, (term, confidence) in enumerate(terms, start=1):
            term_key = f"{index}:{term}"
            confidence_by_term[term_key] = [round(confidence, 2)]

            weight = max(len(term), 1)
            term_seconds = total_seconds * (weight / total_weight) if total_weight else 0.0
            conversion_time_by_term[term_key] = self._format_seconds(term_seconds)

        return {
            "confidence_by_term": confidence_by_term,
            "conversion_time_by_term": conversion_time_by_term,
            "total_conversion_time": self._format_seconds(total_seconds),
        }

    def preprocess_for_classification(self, image_bytes: bytes, classification: str) -> np.ndarray:
        return preprocess_image(image_bytes, classification)

    def process_with_classification(self, image_bytes: bytes, classification: str) -> Dict[str, Any]:
        preprocessed = self.preprocess_for_classification(image_bytes=image_bytes, classification=classification)
        result = self.process({"original": image_bytes, "preprocessed": preprocessed})
        result.setdefault("_meta", {})
        result["_meta"]["preprocessing"] = {
            "classification": classification,
            "shape": list(preprocessed.shape),
            "dtype": str(preprocessed.dtype),
        }
        return result

    def _render_pdf_pages(self, pdf_bytes: bytes, dpi: int = 160) -> list[np.ndarray]:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pages: list[np.ndarray] = []
        for page in document:
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            rgb = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3)
            pages.append(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        document.close()
        return pages

    def _process_pdf_page(self, page_image: np.ndarray) -> Dict[str, Any]:
        process_start = time.perf_counter()
        gray = self._decode_to_gray(page_image)
        resized = cv2.resize(gray, None, fx=1.25, fy=1.25, interpolation=cv2.INTER_CUBIC)
        blur = cv2.GaussianBlur(resized, (3, 3), 0)
        otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        best_text = ""
        best_confidence = -1.0
        best_lang = ""
        for lang in ["por+eng", "eng"]:
            try:
                extracted_text, avg_conf = self._extract_with_data(otsu, lang=lang, psm=6)
            except pytesseract.TesseractError:
                continue
            if len(extracted_text) > len(best_text):
                best_text = extracted_text
                best_confidence = avg_conf
                best_lang = lang

        if not best_text:
            best_text = pytesseract.image_to_string(otsu, lang="eng", config="--oem 3 --psm 6").strip()
            best_confidence = 0.0
            best_lang = "eng"

        return {
            "raw_text": best_text,
            "_meta": {
                "variant_used": "pdf_otsu_fast",
                "lang_used": best_lang,
                "psm_used": 6,
                "avg_confidence": round(best_confidence, 2),
                "ocr_time_seconds": round(time.perf_counter() - process_start, 4),
            },
        }

    def _process_image_source(self, content: Any) -> Dict[str, Any]:
        process_start = time.perf_counter()
        preprocessed_for_metrics = None
        source_for_ocr = content
        if isinstance(content, dict):
            preprocessed = content.get("preprocessed")
            original = content.get("original")
            source_for_ocr = preprocessed if preprocessed is not None else original
            preprocessed_for_metrics = preprocessed

        if source_for_ocr is None:
            raise ValueError("No image input provided for OCR")

        gray = self._decode_to_gray(source_for_ocr)
        variants = self._build_variants(gray)

        best_text = ""
        best_confidence = -1.0
        best_variant = ""
        best_lang = ""
        best_psm = -1

        languages = ["por+eng", "eng"]
        psm_values = [6, 11, 3]

        for variant_name, variant_image in variants:
            for lang in languages:
                for psm in psm_values:
                    try:
                        extracted_text, avg_conf = self._extract_with_data(
                            image=variant_image,
                            lang=lang,
                            psm=psm,
                        )
                    except pytesseract.TesseractError:
                        continue

                    if not extracted_text:
                        continue

                    score = avg_conf * max(len(extracted_text), 1)
                    best_score = best_confidence * max(len(best_text), 1) if best_text else -1

                    if score > best_score:
                        best_text = extracted_text
                        best_confidence = avg_conf
                        best_variant = variant_name
                        best_lang = lang
                        best_psm = psm

        if not best_text:
            best_text = pytesseract.image_to_string(gray, lang="eng", config="--oem 3 --psm 6").strip()
            best_confidence = 0.0
            best_variant = "gray_fallback"
            best_lang = "eng"
            best_psm = 6

        total_ocr_seconds = time.perf_counter() - process_start
        metrics_source = preprocessed_for_metrics if preprocessed_for_metrics is not None else gray
        term_metrics = self._build_term_metrics(
            image=metrics_source,
            lang=best_lang,
            psm=best_psm,
            total_seconds=total_ocr_seconds,
        )

        return {
            "raw_text": best_text,
            "raw_text_fallback": best_text,
            "document_info": {},
            "entities": {},
            "tables": [],
            "totals": {},
            "_meta": {
                "engine": "tesseract",
                "variant_used": best_variant,
                "lang_used": best_lang,
                "psm_used": best_psm,
                "avg_confidence": round(best_confidence, 2),
                "ocr_time_seconds": round(total_ocr_seconds, 4),
                **term_metrics,
            },
        }

    def process(self, content: Any, metadata: dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Process image or PDF with Tesseract OCR.
        metadata: aceito para satisfazer o contrato BaseOCREngine; não utilizado internamente.
        """
        if isinstance(content, bytes) and content.startswith(b"%PDF"):
            page_results = [
                self._process_pdf_page(page_image)
                for page_image in self._render_pdf_pages(content)
            ]
            raw_text = "\n\n".join(result.get("raw_text", "") for result in page_results).strip()
            page_meta = [result.get("_meta", {}) for result in page_results]
            avg_confidences = [
                meta.get("avg_confidence")
                for meta in page_meta
                if isinstance(meta.get("avg_confidence"), (int, float))
            ]
            avg_confidence = float(np.mean(avg_confidences)) if avg_confidences else 0.0
            return {
                "raw_text": raw_text,
                "raw_text_fallback": raw_text,
                "document_info": {
                    "page_count": len(page_results),
                },
                "entities": {},
                "tables": [],
                "totals": {},
                "_meta": {
                    "engine": "tesseract",
                    "input_type": "pdf",
                    "page_count": len(page_results),
                    "avg_confidence": round(avg_confidence, 2),
                    "pages": page_meta,
                },
            }

        return self._process_image_source(content)
