from __future__ import annotations

import time
from typing import Any, Dict, List

import cv2
import numpy as np

from utils.preprocessing import decode_image, preprocess_for_easyocr_engine


class EasyOCREngine:
    def __init__(self):
        try:
            import easyocr
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "EasyOCR não está instalado. Instale com: pip install easyocr"
            ) from exc

        self.reader = easyocr.Reader(["pt", "en"])

    @staticmethod
    def _format_seconds(seconds_value: float) -> str:
        return f"({seconds_value:.1f}s)"

    def _decode_to_rgb(self, image_data: Any) -> np.ndarray:
        image = decode_image(image_data)
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def _build_term_metrics(self, terms: List[tuple[str, float]], total_seconds: float) -> Dict[str, Any]:
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

    def _extract_text(self, image_rgb: np.ndarray) -> tuple[str, float, List[tuple[str, float]]]:
        # PASSO CRÍTICO: leitura OCR com coordenadas + confiança por fragmento.
        results = self.reader.readtext(image_rgb, detail=1, paragraph=False)

        terms: List[tuple[str, float]] = []
        for item in results:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue

            text = str(item[1]).strip()
            if not text:
                continue

            try:
                confidence = float(item[2])
            except (TypeError, ValueError):
                continue

            if 0.0 <= confidence <= 1.0:
                confidence *= 100.0

            confidence = max(0.0, min(100.0, confidence))
            terms.append((text, confidence))

        raw_text = " ".join(text for text, _ in terms).strip()
        avg_confidence = float(np.mean([conf for _, conf in terms])) if terms else 0.0
        return raw_text, avg_confidence, terms

    def process_with_classification(self, image_bytes: bytes, classification: str) -> Dict[str, Any]:
        # PASSO CRÍTICO: preprocess dedicado para EasyOCR (denoise/CLAHE/deskew/upscale).
        preprocessed_bytes, preprocess_meta = preprocess_for_easyocr_engine(
            image_bytes=image_bytes,
            classification=classification,
        )

        result = self.process({"original": image_bytes, "preprocessed": preprocessed_bytes})
        result.setdefault("_meta", {})
        result["_meta"]["preprocessing"] = preprocess_meta
        return result

    def process(self, image_data: Any) -> Dict[str, Any]:
        process_start = time.perf_counter()

        source_for_ocr = image_data
        if isinstance(image_data, dict):
            source_for_ocr = image_data.get("preprocessed") or image_data.get("original")

        if source_for_ocr is None:
            raise ValueError("No image input provided for EasyOCR")

        image_rgb = self._decode_to_rgb(source_for_ocr)
        raw_text, avg_confidence, terms = self._extract_text(image_rgb)

        # Regra operacional sugerida: recomendar fallback quando confiança média < 80%.
        fallback_recommended = avg_confidence < 80.0

        total_ocr_seconds = time.perf_counter() - process_start
        term_metrics = self._build_term_metrics(terms=terms, total_seconds=total_ocr_seconds)

        return {
            "raw_text": raw_text,
            "raw_text_fallback": (
                "EasyOCR detectou baixa confiança; fallback recomendado."
                if fallback_recommended
                else raw_text
            ),
            "document_info": {},
            "entities": {},
            "tables": [],
            "totals": {},
            "_meta": {
                "engine": "easyocr",
                "avg_confidence": round(avg_confidence, 2),
                "ocr_time_seconds": round(total_ocr_seconds, 4),
                "text_length": len(raw_text),
                "fallback_recommended": fallback_recommended,
                **term_metrics,
            },
        }
