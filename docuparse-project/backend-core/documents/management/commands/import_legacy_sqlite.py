from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from documents.models import Document, DocumentEvent, ExtractionResult, Tenant


def _uuid(value: str) -> uuid.UUID:
    return uuid.UUID(str(value))


def _datetime(value: str):
    parsed = parse_datetime(value)
    if parsed is None:
        raise CommandError(f"Invalid datetime value in legacy database: {value!r}")
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_default_timezone())
    return parsed


def _json(value: str):
    if not value:
        return {}
    return json.loads(value)


class Command(BaseCommand):
    help = "Import documents and OCR results from the previous local SQLite database."

    def add_arguments(self, parser):
        parser.add_argument("sqlite_path", type=Path)

    def handle(self, *args, **options):
        sqlite_path: Path = options["sqlite_path"]
        if not sqlite_path.exists():
            raise CommandError(f"SQLite database not found: {sqlite_path}")

        connection = sqlite3.connect(sqlite_path)
        connection.row_factory = sqlite3.Row

        imported_documents = 0
        imported_results = 0
        imported_events = 0
        skipped_documents = 0

        with transaction.atomic():
            tenants = {}
            for row in connection.execute("select * from documents_tenant"):
                tenant, _ = Tenant.objects.get_or_create(
                    slug=row["slug"],
                    defaults={
                        "name": row["name"],
                        "is_active": bool(row["is_active"]),
                    },
                )
                tenants[row["id"]] = tenant

            for row in connection.execute("select * from documents_document order by created_at"):
                document_id = _uuid(row["id"])
                if Document.objects.filter(id=document_id).exists():
                    skipped_documents += 1
                    continue

                document = Document.objects.create(
                    id=document_id,
                    tenant=tenants[row["tenant_id"]],
                    status=row["status"],
                    channel=row["channel"],
                    file_uri=row["file_uri"],
                    raw_text_uri=row["raw_text_uri"],
                    original_filename=row["original_filename"],
                    content_type=row["content_type"],
                    size_bytes=row["size_bytes"],
                    document_type=row["document_type"],
                    layout=row["layout"],
                    correlation_id=_uuid(row["correlation_id"]),
                    received_at=_datetime(row["received_at"]),
                    metadata=_json(row["metadata"]),
                )
                Document.objects.filter(id=document.id).update(
                    created_at=_datetime(row["created_at"]),
                    updated_at=_datetime(row["updated_at"]),
                )
                imported_documents += 1

            for row in connection.execute("select * from documents_extractionresult order by created_at"):
                document_id = _uuid(row["document_id"])
                if not Document.objects.filter(id=document_id).exists():
                    continue
                result, created = ExtractionResult.objects.update_or_create(
                    document_id=document_id,
                    defaults={
                        "id": _uuid(row["id"]),
                        "schema_id": row["schema_id"],
                        "schema_version": row["schema_version"],
                        "fields": _json(row["fields"]),
                        "confidence": row["confidence"],
                        "requires_human_validation": bool(row["requires_human_validation"]),
                    },
                )
                ExtractionResult.objects.filter(id=result.id).update(
                    created_at=_datetime(row["created_at"]),
                    updated_at=_datetime(row["updated_at"]),
                )
                if created:
                    imported_results += 1

            for row in connection.execute("select * from documents_documentevent order by created_at"):
                event_id = _uuid(row["event_id"])
                if DocumentEvent.objects.filter(event_id=event_id).exists():
                    continue
                document_id = _uuid(row["document_id"]) if row["document_id"] else None
                event = DocumentEvent.objects.create(
                    id=_uuid(row["id"]),
                    event_id=event_id,
                    tenant=tenants[row["tenant_id"]],
                    document_id=document_id,
                    event_type=row["event_type"],
                    event_version=row["event_version"],
                    correlation_id=_uuid(row["correlation_id"]),
                    source=row["source"],
                    occurred_at=_datetime(row["occurred_at"]),
                    payload=_json(row["payload"]),
                )
                DocumentEvent.objects.filter(id=event.id).update(
                    created_at=_datetime(row["created_at"]),
                    updated_at=_datetime(row["updated_at"]),
                )
                imported_events += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Imported "
                f"{imported_documents} documents, "
                f"{imported_results} extraction results, "
                f"{imported_events} events; "
                f"skipped {skipped_documents} existing documents."
            )
        )
