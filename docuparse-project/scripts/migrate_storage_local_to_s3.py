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

from docuparse_storage import LocalStorage, S3Storage  # noqa: F401 - re-export p/ testes existentes

# Lógica pura vive em docuparse_storage.migration (compartilhada com o management
# command migrate_storage_local_to_s3). Re-exportada aqui para manter a API do
# script (e seus testes) estável.
from docuparse_storage.migration import (  # noqa: F401
    LOCAL_PREFIX,
    MigrationStats,
    migrate_documents,
    migrate_uri,
)

logger = logging.getLogger("migrate_storage")


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
    print(
        f"Migração local:// → s3:// [{'DRY-RUN' if args.dry_run else 'APLICADO'}] "
        f"escaneados={stats.scanned} migrados={stats.migrated} "
        f"pulados={stats.skipped} sem_arquivo={len(stats.missing)} erros={len(stats.errors)}"
    )
    for item in stats.missing:
        print(f"  sem arquivo no disco (ignorado): {item}")
    for err in stats.errors:
        print(f"  ERRO inesperado: {err}")
    # Arquivo ausente NÃO é falha (binário já perdido); só erro inesperado dá exit≠0.
    return 1 if stats.errors else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
