"""Lógica pura de migração de artefatos ``local://`` → ``s3://`` (feature 011).

Django-agnóstica: ``migrate_documents`` recebe um iterável de objetos com
duck-typing (atributos ``file_uri``/``raw_text_uri`` e ``save(update_fields=...)``).
Reutilizada tanto pelo script standalone (``scripts/migrate_storage_local_to_s3.py``)
quanto pelo management command ``migrate_storage_local_to_s3``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .local import LocalStorage
from .s3 import S3Storage

LOCAL_PREFIX = "local://"


@dataclass
class MigrationStats:
    scanned: int = 0
    migrated: int = 0
    skipped: int = 0
    # Objetos local:// cujo arquivo não existe mais no disco. NÃO é erro fatal:
    # o binário já estava perdido, então não há o que migrar — apenas registramos.
    missing: list[str] = field(default_factory=list)
    # Falhas inesperadas (ex.: S3 indisponível) — estas, sim, merecem atenção.
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
            except FileNotFoundError:
                # Arquivo local já não existe: nada a migrar. Mantém a URI intacta
                # (não perde o registro) e segue — não é erro fatal.
                stats.missing.append(f"{getattr(document, 'id', '?')}:{field_name}")
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
