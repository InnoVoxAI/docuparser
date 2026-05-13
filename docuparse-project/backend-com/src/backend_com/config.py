from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[3]


def _env(key: str, default: str = "") -> str:
    """Read an env var and strip surrounding whitespace and optional shell quotes.

    Docker Compose env_file can pass values with literal quote characters
    (e.g. KEY="value") that os.environ preserves verbatim. This helper
    normalises those so the app always works regardless of how the shell
    or Docker runtime delivered the value.
    """
    raw = os.environ.get(key)
    if raw is None:
        return default
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1].strip()
    return value


class Settings:
    service_name = "docuparse-backend-com"
    local_storage_dir = Path(_env("DOCUPARSE_LOCAL_STORAGE_DIR", str(PROJECT_DIR / ".docuparse-storage")))
    local_event_dir = Path(_env("DOCUPARSE_LOCAL_EVENT_DIR", str(PROJECT_DIR / ".docuparse-events")))
    max_upload_bytes = int(_env("DOCUPARSE_MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
    email_webhook_token = _env("DOCUPARSE_EMAIL_WEBHOOK_TOKEN")
    whatsapp_webhook_token = _env("DOCUPARSE_WHATSAPP_WEBHOOK_TOKEN")
    internal_service_token = _env("DOCUPARSE_INTERNAL_SERVICE_TOKEN")
    backend_core_document_received_url = _env(
        "BACKEND_CORE_DOCUMENT_RECEIVED_URL",
        "http://127.0.0.1:8000/api/ocr/events/document-received",
    )
    backend_core_email_settings_url = _env(
        "BACKEND_CORE_EMAIL_SETTINGS_URL",
        "http://127.0.0.1:8000/api/ocr/settings/email",
    )
    imap_password = _env("DOCUPARSE_IMAP_PASSWORD") or _env("imap_reader_password")
    imap_poll_limit = int(_env("DOCUPARSE_IMAP_POLL_LIMIT", "10"))
    imap_mark_as_read = _env("DOCUPARSE_IMAP_MARK_AS_READ", "false").lower() in {"1", "true", "yes"}
    imap_timeout_seconds = int(_env("DOCUPARSE_IMAP_TIMEOUT_SECONDS", "20"))
    cors_allowed_origins = [
        value.strip()
        for value in _env("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if value.strip()
    ]


settings = Settings()
