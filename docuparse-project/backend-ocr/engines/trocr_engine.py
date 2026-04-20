from __future__ import annotations

import re
import time
import importlib
from typing import Any, Dict

import cv2
import numpy as np

from utils.preprocessing import decode_image, preprocess_for_trocr_engine, preprocess_for_trocr_region


class TrOCREngine:
	def __init__(self):
		try:
			torch = importlib.import_module("torch")
			transformers = importlib.import_module("transformers")
		except ModuleNotFoundError as exc:
			raise RuntimeError(
				"TrOCR não está instalado. Instale com: pip install transformers torch torchvision"
			) from exc

		self._torch = torch
		self._processor_cls = transformers.TrOCRProcessor
		self._model_cls = transformers.VisionEncoderDecoderModel
		self._processor = None
		self._model = None
		self._device = "cuda" if torch.cuda.is_available() else "cpu"

	def _ensure_model(self) -> None:
		if self._processor is not None and self._model is not None:
			return

		# PASSO CRÍTICO: checkpoint voltado para manuscrito.
		self._processor = self._processor_cls.from_pretrained("microsoft/trocr-base-handwritten")
		self._model = self._model_cls.from_pretrained("microsoft/trocr-base-handwritten")
		self._model.to(self._device)
		self._model.eval()

	@staticmethod
	def _normalize_text(text: str) -> str:
		# PASSO CRÍTICO: normaliza ambiguidades OCR em tokens numéricos.
		if not text:
			return ""

		replacements = {
			"O": "0",
			"I": "1",
			"S": "5",
			"o": "0",
			"i": "1",
			"s": "5",
		}

		tokens = text.split()
		normalized_tokens = []
		for token in tokens:
			has_digit_or_symbol = bool(re.search(r"[\d/\-.]", token))
			if has_digit_or_symbol:
				token = "".join(replacements.get(char, char) for char in token)
			normalized_tokens.append(token)

		return " ".join(normalized_tokens).strip()

	@staticmethod
	def _decode_to_bgr(image_data: Any) -> np.ndarray:
		return decode_image(image_data)

	def process_region(self, region_image: np.ndarray) -> Dict[str, Any]:
		region_start = time.perf_counter()
		self._ensure_model()

		prepared = preprocess_for_trocr_region(region_image)
		image_rgb = cv2.cvtColor(prepared, cv2.COLOR_BGR2RGB)

		from PIL import Image

		pil_image = Image.fromarray(image_rgb)
		pixel_values = self._processor(images=pil_image, return_tensors="pt").pixel_values
		pixel_values = pixel_values.to(self._device)

		with self._torch.no_grad():
			generated_ids = self._model.generate(pixel_values, max_new_tokens=128)

		decoded_text = self._processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
		normalized_text = self._normalize_text(decoded_text)

		elapsed = time.perf_counter() - region_start
		return {
			"text": normalized_text,
			"raw_text": decoded_text.strip(),
			"processing_time_seconds": round(elapsed, 4),
			"engine": "trocr",
		}

	def process_with_classification(self, image_bytes: bytes, classification: str) -> Dict[str, Any]:
		preprocessed_bytes, preprocess_meta = preprocess_for_trocr_engine(
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
			raise ValueError("No image input provided for TrOCR")

		image_bgr = self._decode_to_bgr(source_for_ocr)
		region_result = self.process_region(image_bgr)
		text = str(region_result.get("text") or "").strip()

		total_ocr_seconds = time.perf_counter() - process_start
		heuristic_confidence = 92.0 if text else 0.0

		return {
			"raw_text": text,
			"raw_text_fallback": text,
			"document_info": {},
			"entities": {},
			"tables": [],
			"totals": {},
			"_meta": {
				"engine": "trocr",
				"avg_confidence": round(heuristic_confidence, 2),
				"ocr_time_seconds": round(total_ocr_seconds, 4),
				"text_length": len(text),
				"fallback_recommended": len(text) == 0,
			},
		}
