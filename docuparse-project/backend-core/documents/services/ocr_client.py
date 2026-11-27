import mimetypes
from typing import Any

from django.conf import settings

from documents.services.service_errors import request_json

SERVICE_NAME = "backend-ocr"


class OCRClient:
    def __init__(self):
        self.base_url = getattr(settings, "BACKEND_OCR_URL", "http://backend-ocr:8080")

    def list_engines(self) -> list[dict[str, str]]:
        """
        Retrieves available OCR engines from backend-ocr.
        """
        url = f"{self.base_url}/api/v1/engines"
        return request_json(SERVICE_NAME, "GET", url, timeout=30)

    def process_document(
        self,
        file_obj,
        filename: str,
        engine: str | None = None,
        *,
        legacy_extraction: bool = False,
    ) -> dict[str, Any]:
        """
        Sends the file to backend-ocr for processing.

        Raises TransientServiceError / PermanentServiceError (ver service_errors).
        """
        url = f"{self.base_url}/api/v1/process"
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        files = {"file": (filename, file_obj, mime_type)}
        data = {"legacy_extraction": str(legacy_extraction).lower()}
        if engine:
            data["selected_engine"] = engine

        return request_json(
            SERVICE_NAME, "POST", url, files=files, data=data, timeout=300
        )
