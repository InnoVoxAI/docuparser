from __future__ import annotations

import io
import re
import time
from typing import Any, Dict, List


class LlamaParseEngine:
    def _normalize_input(self, file_path_or_bytes: Any) -> bytes:
        if isinstance(file_path_or_bytes, bytes):
            return file_path_or_bytes

        if isinstance(file_path_or_bytes, str):
            with open(file_path_or_bytes, "rb") as file_obj:
                return file_obj.read()

        if hasattr(file_path_or_bytes, "read"):
            content = file_path_or_bytes.read()
            if isinstance(content, bytes):
                return content

        if isinstance(file_path_or_bytes, io.BytesIO):
            return file_path_or_bytes.getvalue()

        raise ValueError("LlamaParseEngine expected file bytes or file path")

    def _read_pdf_text_by_page(self, pdf_bytes: bytes) -> List[str]:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(pdf_bytes)
        page_texts: List[str] = []

        for idx in range(len(pdf)):
            page = pdf.get_page(idx)
            text_page = page.get_textpage()
            page_texts.append((text_page.get_text_bounded() or "").strip())

        return page_texts

    def _clean_text(self, text: str) -> str:
        # PASSO CRÍTICO: limpeza leve para remover duplicações e ruído de blocos.
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        deduped_lines: List[str] = []
        seen = set()
        for line in lines:
            key = re.sub(r"\s+", " ", line.lower())
            if key in seen:
                continue
            seen.add(key)
            deduped_lines.append(line)

        return "\n".join(deduped_lines)

    def _group_semantic_blocks(self, page_texts: List[str]) -> Dict[str, Any]:
        pages = []
        for page_index, text in enumerate(page_texts, start=1):
            clean_text = self._clean_text(text)
            lines = [line for line in clean_text.splitlines() if line.strip()]

            title = lines[0] if lines else ""
            body = lines[1:] if len(lines) > 1 else []
            table_like = [line for line in body if ("|" in line or "\t" in line)]

            pages.append(
                {
                    "page": page_index,
                    "title": title,
                    "body": body,
                    "table_like_lines": table_like,
                }
            )

        return {
            "pages": pages,
            "table_blocks": [
                {"page": page["page"], "rows": page["table_like_lines"]}
                for page in pages
                if page["table_like_lines"]
            ],
        }

    def process_with_classification(self, file_bytes: bytes, classification: str) -> Dict[str, Any]:
        result = self.process(file_bytes)
        result.setdefault("_meta", {})
        result["_meta"]["classification"] = classification
        return result

    def process(self, file_path_or_bytes: Any) -> Dict[str, Any]:
        process_start = time.perf_counter()
        raw_bytes = self._normalize_input(file_path_or_bytes)

        # PASSO CRÍTICO: processamento por páginas e blocos semânticos.
        page_texts = self._read_pdf_text_by_page(raw_bytes)
        semantic = self._group_semantic_blocks(page_texts)

        raw_text = "\n\n".join(
            self._clean_text(page_text)
            for page_text in page_texts
            if page_text.strip()
        ).strip()

        avg_confidence = round(min(100.0, len(raw_text) / 35.0), 2)
        fallback_recommended = avg_confidence < 65.0 or not raw_text
        elapsed = time.perf_counter() - process_start

        return {
            "raw_text": raw_text,
            "raw_text_fallback": (
                "LlamaParse retornou pouco conteúdo; revisar fallback adicional."
                if fallback_recommended
                else raw_text
            ),
            "document_info": {
                "page_count": len(page_texts),
            },
            "entities": {
                "semantic_pages": semantic["pages"],
            },
            "tables": semantic["table_blocks"],
            "totals": {},
            "json_structure": semantic,
            "_meta": {
                "engine": "llamaparse",
                "avg_confidence": avg_confidence,
                "ocr_time_seconds": round(elapsed, 4),
                "fallback_recommended": fallback_recommended,
            },
        }
