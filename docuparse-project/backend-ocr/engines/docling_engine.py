from __future__ import annotations

import io
import re
import time
from typing import Any, Dict, List


class DoclingEngine:
    def __init__(self):
        # Comentário importante:
        # Preferimos PDF original e não rasterizamos quando há camada textual.
        self.required_patterns = {
            "date": re.compile(r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b"),
            "currency": re.compile(r"\b\d{1,3}(?:\.\d{3})*,\d{2}\b"),
            "document_number": re.compile(r"\b\d{6,}\b"),
        }

    def _read_pdf_text_by_page(self, pdf_bytes: bytes) -> List[str]:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(pdf_bytes)
        page_texts: List[str] = []

        for idx in range(len(pdf)):
            page = pdf.get_page(idx)
            text_page = page.get_textpage()
            page_texts.append((text_page.get_text_bounded() or "").strip())

        return page_texts

    def _extract_structured_blocks(self, page_texts: List[str]) -> Dict[str, Any]:
        blocks = []
        tables = []

        for page_index, page_text in enumerate(page_texts, start=1):
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            if not lines:
                continue

            header = lines[:3]
            footer = lines[-2:] if len(lines) > 2 else []
            body = lines[3:-2] if len(lines) > 5 else lines

            # Heurística simples para detectar conteúdo tabular em PDFs digitais.
            maybe_table_lines = [line for line in body if ("|" in line or "\t" in line)]
            if maybe_table_lines:
                tables.append(
                    {
                        "page": page_index,
                        "rows": maybe_table_lines,
                    }
                )

            blocks.append(
                {
                    "page": page_index,
                    "header": header,
                    "body": body,
                    "footer": footer,
                }
            )

        return {
            "blocks": blocks,
            "tables": tables,
        }

    def _validate_required_signals(self, raw_text: str) -> Dict[str, bool]:
        return {
            key: bool(pattern.search(raw_text))
            for key, pattern in self.required_patterns.items()
        }

    def _normalize_input(self, pdf_path_or_bytes: Any) -> bytes:
        if isinstance(pdf_path_or_bytes, bytes):
            return pdf_path_or_bytes

        if isinstance(pdf_path_or_bytes, str):
            with open(pdf_path_or_bytes, "rb") as file_obj:
                return file_obj.read()

        if hasattr(pdf_path_or_bytes, "read"):
            content = pdf_path_or_bytes.read()
            if isinstance(content, bytes):
                return content

        if isinstance(pdf_path_or_bytes, io.BytesIO):
            return pdf_path_or_bytes.getvalue()

        raise ValueError("DoclingEngine expected PDF bytes or file path")

    def process_with_classification(self, pdf_bytes: bytes, classification: str) -> Dict[str, Any]:
        # Mantemos assinatura compatível com o padrão dos demais engines.
        result = self.process(pdf_bytes)
        result.setdefault("_meta", {})
        result["_meta"]["classification"] = classification
        return result

    def process(self, pdf_path_or_bytes: Any) -> Dict[str, Any]:
        process_start = time.perf_counter()
        pdf_bytes = self._normalize_input(pdf_path_or_bytes)

        # PASSO CRÍTICO: trabalhar por página no PDF original.
        page_texts = self._read_pdf_text_by_page(pdf_bytes)
        structured = self._extract_structured_blocks(page_texts)

        full_text = "\n\n".join(text for text in page_texts if text).strip()
        required_signals = self._validate_required_signals(full_text)
        missing_fields = not all(required_signals.values())

        # Score heurístico: mais caracteres e sinais válidos indicam melhor qualidade estrutural.
        text_score = min(100.0, len(full_text) / 40.0)
        signal_score = (sum(1 for value in required_signals.values() if value) / len(required_signals)) * 100.0
        avg_confidence = round((text_score * 0.4) + (signal_score * 0.6), 2)

        fallback_recommended = missing_fields or avg_confidence < 70.0
        elapsed = time.perf_counter() - process_start

        return {
            "raw_text": full_text,
            "raw_text_fallback": (
                "Docling detectou campos obrigatórios ausentes; fallback recomendado."
                if fallback_recommended
                else full_text
            ),
            "document_info": {
                "page_count": len(page_texts),
                "non_empty_pages": sum(1 for text in page_texts if text.strip()),
            },
            "entities": {
                "required_signals": required_signals,
                "layout_blocks": structured["blocks"],
            },
            "tables": structured["tables"],
            "totals": {},
            "_meta": {
                "engine": "docling",
                "document_type": "digital_pdf",
                "avg_confidence": avg_confidence,
                "ocr_time_seconds": round(elapsed, 4),
                "missing_fields": missing_fields,
                "fallback_recommended": fallback_recommended,
            },
        }
