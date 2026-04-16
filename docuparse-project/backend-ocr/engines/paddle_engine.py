from typing import Dict, Any


class PaddleOCREngine:
	def process(self, image_data: Any) -> Dict[str, Any]:
		"""
		Process image with PaddleOCR.
		"""
		_ = image_data
		return {
			"raw_text_fallback": "PaddleOCR executado (placeholder de integração)",
			"_meta": {
				"engine": "paddleocr",
			},
		}

