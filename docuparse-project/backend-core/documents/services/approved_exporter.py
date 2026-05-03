from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

from documents.models import Document


def export_approved_document_json(document: Document, payload: dict) -> Path:
    export_root = Path(settings.DOCUPARSE_APPROVED_EXPORT_DIR)
    target_dir = export_root / document.tenant.slug
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{document.id}.json"

    export_payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "document_id": str(document.id),
        "tenant_id": document.tenant.slug,
        "status": document.status,
        "correlation_id": str(document.correlation_id),
        "payload": payload,
    }
    target_path.write_text(
        json.dumps(export_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target_path
