from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[3]


class Settings:
    service_name = "docuparse-backend-com"
    local_storage_dir = Path(os.environ.get("DOCUPARSE_LOCAL_STORAGE_DIR", str(PROJECT_DIR / ".docuparse-storage")))
    local_event_dir = Path(os.environ.get("DOCUPARSE_LOCAL_EVENT_DIR", str(PROJECT_DIR / ".docuparse-events")))
    max_upload_bytes = int(os.environ.get("DOCUPARSE_MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
    email_webhook_token = os.environ.get("DOCUPARSE_EMAIL_WEBHOOK_TOKEN", "").strip()
    whatsapp_webhook_token = os.environ.get("DOCUPARSE_WHATSAPP_WEBHOOK_TOKEN", "").strip()
    internal_service_token = os.environ.get("DOCUPARSE_INTERNAL_SERVICE_TOKEN", "").strip()
    backend_core_document_received_url = os.environ.get(
        "BACKEND_CORE_DOCUMENT_RECEIVED_URL",
        "http://127.0.0.1:8000/api/ocr/events/document-received",
    ).strip()
    cors_allowed_origins = [
        value.strip()
        for value in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if value.strip()
    ]


settings = Settings()
