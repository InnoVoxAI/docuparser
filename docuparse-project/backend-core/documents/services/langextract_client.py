from typing import Any

from django.conf import settings

from documents.services.service_errors import request_json

SERVICE_NAME = "langextract-service"


class LangExtractClient:
    def __init__(self):
        self.base_url = getattr(
            settings, "LANGEXTRACT_SERVICE_URL", "http://langextract-service:8091"
        )

    def extract_with_schema(
        self,
        raw_text: str,
        schema_definition: dict[str, Any],
        layout: str = "generic",
        document_type: str = "unknown",
    ) -> dict[str, Any]:
        """Call the langextract-service LLM extraction endpoint synchronously.

        Raises TransientServiceError / PermanentServiceError (ver service_errors).
        """
        url = f"{self.base_url}/api/v1/extract"
        payload = {
            "raw_text": raw_text,
            "layout": layout,
            "document_type": document_type,
            "schema_definition": schema_definition,
        }
        return request_json(SERVICE_NAME, "POST", url, json=payload, timeout=120)
