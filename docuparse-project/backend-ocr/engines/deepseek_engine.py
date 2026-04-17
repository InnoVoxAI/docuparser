from __future__ import annotations

import base64
import json
import os
import time
import logging
from typing import Any, Dict, Union

from utils.preprocessing import preprocess_for_deepseek_engine


logger = logging.getLogger(__name__)


class DeepSeekEngine:
    def __init__(self):
        # PASSO CRÍTICO: configuração do endpoint multimodal (compatível com OpenAI API).
        self.base_url = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434/v1")
        self.api_key = os.getenv("OLLAMA_API_KEY", "ollama")
        self.model = os.getenv("OLLAMA_MODEL", "deepseek-r1")

        self._init_error: str | None = None
        self._http_client = None
        self.client = None
        try:
            from openai import OpenAI
            import httpx

            self._http_client = httpx.Client(
                timeout=httpx.Timeout(60.0, connect=10.0),
            )

            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=self._http_client,
            )
        except Exception as exc:
            self._init_error = str(exc)
            logger.warning("DeepSeek client init failed: %s", self._init_error)

    def is_available(self) -> bool:
        return self.client is not None

    def get_init_error(self) -> str | None:
        return self._init_error

    def _encode_image(self, image_path_or_bytes: Union[str, bytes]) -> str:
        if isinstance(image_path_or_bytes, str):
            with open(image_path_or_bytes, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        return base64.b64encode(image_path_or_bytes).decode("utf-8")

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

        raise ValueError("DeepSeekEngine expected bytes or file path")

    def _extract_text(self, image_bytes: bytes) -> Dict[str, Any]:
        if self.client is None:
            raise RuntimeError(f"DeepSeek client unavailable: {self._init_error}")

        base64_image = self._encode_image(image_bytes)

        # PASSO CRÍTICO: prompt estruturado para extração OCR/semântica.
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extraia texto e campos relevantes do documento. "
                                "Retorne JSON com chaves: raw_text, document_info, entities, tables, totals."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")
        elif "```" in content:
            content = content.replace("```", "")

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        return {"raw_text": str(content).strip()}

    def process_with_classification(self, image_bytes: bytes, classification: str) -> Dict[str, Any]:
        # PASSO CRÍTICO: preprocess por ROI para cenários manuscritos/complexos.
        preprocessed_bytes, preprocess_meta = preprocess_for_deepseek_engine(
            image_bytes=image_bytes,
            classification=classification,
        )

        result = self.process({"original": image_bytes, "preprocessed": preprocessed_bytes})
        result.setdefault("_meta", {})
        result["_meta"]["preprocessing"] = preprocess_meta
        result["_meta"]["classification"] = classification
        return result

    def process(self, file_path_or_bytes: Any) -> Dict[str, Any]:
        process_start = time.perf_counter()
        source = file_path_or_bytes

        if isinstance(file_path_or_bytes, dict):
            source = file_path_or_bytes.get("preprocessed") or file_path_or_bytes.get("original")

        if source is None:
            raise ValueError("No input provided for DeepSeek")

        try:
            image_bytes = self._normalize_input(source)
            extracted = self._extract_text(image_bytes)

            raw_text = str(extracted.get("raw_text", "")).strip()
            avg_confidence = 90.0 if raw_text else 0.0
            fallback_recommended = avg_confidence < 75.0

            elapsed = time.perf_counter() - process_start
            return {
                "raw_text": raw_text,
                "raw_text_fallback": (
                    "DeepSeek retornou conteúdo insuficiente; fallback recomendado."
                    if fallback_recommended
                    else raw_text
                ),
                "document_info": extracted.get("document_info", {}),
                "entities": extracted.get("entities", {}),
                "tables": extracted.get("tables", []),
                "totals": extracted.get("totals", {}),
                "_meta": {
                    "engine": "deepseek",
                    "model": self.model,
                    "avg_confidence": avg_confidence,
                    "ocr_time_seconds": round(elapsed, 4),
                    "fallback_recommended": fallback_recommended,
                    "engine_available": self.client is not None,
                },
            }
        except Exception as exc:
            elapsed = time.perf_counter() - process_start
            return {
                "raw_text": "",
                "raw_text_fallback": f"Failed to process with DeepSeek: {exc}",
                "document_info": {},
                "entities": {},
                "tables": [],
                "totals": {},
                "_meta": {
                    "engine": "deepseek",
                    "avg_confidence": 0.0,
                    "ocr_time_seconds": round(elapsed, 4),
                    "fallback_recommended": True,
                    "error": str(exc),
                    "engine_available": self.client is not None,
                },
            }
