from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

from documents.models import Document


def export_approved_document_json(
    document: Document,
    payload: dict,
    *,
    export_root: str | Path | None = None,
    export_format: str = "json",
) -> Path:
    export_root = Path(export_root or settings.DOCUPARSE_APPROVED_EXPORT_DIR)
    target_dir = export_root / document.tenant.slug
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = "jsonl" if export_format == "jsonl" else "json"
    target_path = target_dir / f"{document.id}.{suffix}"

    export_payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "document_id": str(document.id),
        "tenant_id": document.tenant.slug,
        "status": document.status,
        "correlation_id": str(document.correlation_id),
        "payload": payload,
    }
    if export_format == "jsonl":
        content = json.dumps(export_payload, ensure_ascii=False, sort_keys=True) + "\n"
    else:
        content = json.dumps(export_payload, ensure_ascii=False, indent=2, sort_keys=True)
    target_path.write_text(content, encoding="utf-8")
    return target_path
