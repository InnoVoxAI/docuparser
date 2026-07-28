from __future__ import annotations

import logging

from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from docuparse_storage import get_storage

from documents.models import Document

logger = logging.getLogger(__name__)


@receiver(
    post_delete,
    sender=Document,
    dispatch_uid="documents.delete_document_storage_objects",
)
def delete_document_storage_objects(sender, instance: Document, **kwargs) -> None:
    """Remove os objetos do storage (binário + ``raw_text.json``) quando um
    ``Document`` é apagado, evitando objetos órfãos no MinIO/disco.

    A limpeza é agendada com ``transaction.on_commit`` para só remover os objetos
    **depois** que a exclusão no banco for durável — se a transação der rollback,
    o objeto é preservado. É best-effort e idempotente: um erro ao apagar nunca
    propaga (o registro já foi removido); apenas logamos para reconciliação
    posterior via o command ``reconcile_storage``.
    """
    uris = [uri for uri in (instance.file_uri, instance.raw_text_uri) if uri]
    if not uris:
        return

    document_id = str(instance.id)

    def _cleanup() -> None:
        storage = get_storage()
        for uri in uris:
            try:
                storage.delete(uri)
            except Exception:  # noqa: BLE001 - nunca propagar: o delete do banco já ocorreu
                logger.warning(
                    "document_storage_cleanup_failed",
                    extra={"document_id": document_id, "uri": uri},
                    exc_info=True,
                )

    transaction.on_commit(_cleanup)
