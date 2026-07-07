#!/usr/bin/env python
"""Migração idempotente de artefatos de ``local://`` para ``s3://`` (feature 011).

Para cada ``Document`` com ``file_uri``/``raw_text_uri`` no esquema ``local://``:
lê os bytes do disco local, grava no S3 (mesma key) e atualiza a URI no banco
para ``s3://``. Como o ``RoutingStorage`` resolve por esquema, itens ainda não
migrados continuam legíveis durante todo o processo — logo, a migração é
incremental, retomável e sem downtime.

Uso (a partir do backend-core, com o ambiente S3 configurado):
    python scripts/migrate_storage_local_to_s3.py --dry-run
    python scripts/migrate_storage_local_to_s3.py --apply
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field

from docuparse_storage import LocalStorage, S3Storage

logger = logging.getLogger("migrate_storage")

LOCAL_PREFIX = "local://"


@dataclass
class MigrationStats:
    scanned: int = 0
    migrated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def migrate_uri(uri: str, local: LocalStorage, s3: S3Storage, *, dry_run: bool) -> str:
    """Migra uma única URI. Idempotente: URIs sem ``local://`` são devolvidas
    inalteradas (já migradas ou vazias). Devolve a nova URI (``s3://``)."""
    if not uri or not uri.startswith(LOCAL_PREFIX):
        return uri
    key = uri[len(LOCAL_PREFIX):]
    content = local.get_bytes(uri)  # levanta FileNotFoundError se sumiu (falha explícita)
    if dry_run:
        return f"s3://<bucket>/{key}"
    stored = s3.put_bytes(key, content)
    return stored.uri


def migrate_documents(documents, local: LocalStorage, s3: S3Storage, *, dry_run: bool) -> MigrationStats:
    """Itera um iterável de documentos (duck-typing: atributos ``file_uri`` e
    ``raw_text_uri`` e um ``save(update_fields=...)``), migrando cada artefato.

    Recebe o queryset/iterável por injeção para permitir teste sem Django.
    """
    stats = MigrationStats()
    for document in documents:
        stats.scanned += 1
        changed_fields: list[str] = []
        for field_name in ("file_uri", "raw_text_uri"):
            current = getattr(document, field_name, "") or ""
            if not current.startswith(LOCAL_PREFIX):
                continue
            try:
                new_uri = migrate_uri(current, local, s3, dry_run=dry_run)
            except FileNotFoundError as exc:
                stats.errors.append(f"{getattr(document, 'id', '?')}:{field_name}: {exc}")
                logger.warning("migrate.missing_object", extra={"field": field_name, "uri": current})
                continue
            setattr(document, field_name, new_uri)
            changed_fields.append(field_name)
        if changed_fields and not dry_run:
            document.save(update_fields=changed_fields)
        if changed_fields:
            stats.migrated += 1
        else:
            stats.skipped += 1
    return stats


def _setup_django():  # pragma: no cover - só usado no entrypoint real
    import os
    import sys
    from pathlib import Path

    backend_core = Path(__file__).resolve().parents[1] / "backend-core"
    sys.path.insert(0, str(backend_core))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    import django

    django.setup()


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - entrypoint
    parser = argparse.ArgumentParser(description="Migra artefatos local:// → s3://")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="apenas relata, não grava")
    group.add_argument("--apply", action="store_true", help="executa a migração")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)

    _setup_django()
    from django.conf import settings as dj_settings
    from documents.models import Document

    from docuparse_storage.factory import _build_s3_from_env

    local = LocalStorage(dj_settings.DOCUPARSE_LOCAL_STORAGE_DIR)
    s3 = _build_s3_from_env()  # falha explícita se S3 não estiver configurado

    stats = migrate_documents(Document.objects.all().iterator(), local, s3, dry_run=args.dry_run)
    logger.info(
        "migrate.done",
        extra={
            "dry_run": args.dry_run,
            "scanned": stats.scanned,
            "migrated": stats.migrated,
            "skipped": stats.skipped,
            "errors": len(stats.errors),
        },
    )
    return 1 if stats.errors else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
