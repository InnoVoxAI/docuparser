import mimetypes
from typing import Any, Dict

import requests
from django.conf import settings


class OCRClient:
    def __init__(self):
        self.base_url = getattr(
            settings, 'BACKEND_OCR_URL', 'http://backend-ocr:8080')

    def list_engines(self) -> list[dict[str, str]]:
        """
        Retrieves available OCR engines from backend-ocr.
        """
        url = f"{self.base_url}/api/v1/engines"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    def process_document(
        self,
        file_obj,
        filename: str,
        engine: str | None = None,
        *,
        legacy_extraction: bool = False,
    ) -> Dict[str, Any]:
        """
        Sends the file to backend-ocr for processing.
        """
        url = f"{self.base_url}/api/v1/process"
        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        files = {'file': (filename, file_obj, mime_type)}
        data = {'legacy_extraction': str(legacy_extraction).lower()}
        if engine:
            data['selected_engine'] = engine

        try:
            response = requests.post(url, files=files, data=data, timeout=300)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # Log error
            print(f"Error communicating with OCR backend: {e}")
            raise
