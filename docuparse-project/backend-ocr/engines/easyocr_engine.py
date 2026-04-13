from typing import Dict, Any


class EasyOCREngine:
    def __init__(self):
        try:
            import easyocr
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "EasyOCR não está instalado. Instale com: pip install easyocr"
            ) from exc

        self.reader = easyocr.Reader(['en', 'pt'])

    def process(self, image_data: Any) -> Dict[str, Any]:
        """
        Process image with EasyOCR.
        """
        _ = image_data
        return {"raw_text_fallback": "EasyOCR executado (placeholder de integração)"}
