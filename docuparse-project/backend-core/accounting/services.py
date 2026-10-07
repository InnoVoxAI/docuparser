"""Persistência da classificação do documento e do evento de auditoria.

O estado atual fica em `DocumentClassification`; o histórico, nos `DocumentEvent`
`document.classified` (um por classificação, automática ou manual).
"""

from __future__ import annotations

import json
from typing import Any

from condominiums.models import Condominium
from django.contrib.auth.models import AbstractBaseUser
from django.db import connection, transaction
from documents.models import Document, DocumentEvent
from documents.services.field_versioning import get_active_version
from docuparse_storage import get_storage
from events import DocumentClassifiedEvent
from events.schemas import DocumentClassifiedData, LedgerAccountRef

from accounting.classification import DocumentFacts, classify
from accounting.models import DocumentClassification, LedgerAccount

EVENT_SOURCE = "backend-core"
NO_RULE_REASON = "nenhuma regra encontrou conta"


def _plain_fields(document: Document) -> dict[str, Any]:
    """Campos extraídos como valores simples (o campo pode vir como {value, confidence})."""
    version = get_active_version(document)
    extraction = getattr(document, "extraction_result", None)
    raw_fields = (
        version.fields if version else (extraction.fields if extraction else {})
    )
    plain: dict[str, Any] = {}
    for name, raw in raw_fields.items():
        value = raw.get("value") if isinstance(raw, dict) else raw
        if value not in (None, ""):
            plain[name] = value
    return plain


def _raw_text(document: Document) -> str:
    if not document.raw_text_uri:
        return ""
    payload = json.loads(get_storage().get_bytes(document.raw_text_uri).decode("utf-8"))
    return str(payload.get("raw_text") or "")


def facts_for_document(document: Document) -> DocumentFacts:
    return DocumentFacts(fields=_plain_fields(document), raw_text=_raw_text(document))


def _ref(account: LedgerAccount | None) -> LedgerAccountRef | None:
    if account is None:
        return None
    return LedgerAccountRef(id=account.id, code=account.code, name=account.name)


def _record_classification_event(
    document: Document,
    data: DocumentClassifiedData,
) -> DocumentEvent:
    tenant = connection.tenant
    event = DocumentClassifiedEvent(
        tenant_id=getattr(tenant, "slug", "") or connection.schema_name,
        document_id=document.id,
        correlation_id=document.correlation_id,
        source=EVENT_SOURCE,
        data=data,
    )
    return DocumentEvent.objects.create(
        event_id=event.event_id,
        document=document,
        event_type=event.event_type,
        event_version=event.event_version,
        correlation_id=event.correlation_id,
        source=event.source,
        occurred_at=event.occurred_at,
        payload=event.model_dump(mode="json"),
    )


def _lock(document: Document) -> DocumentClassification | None:
    """Serializa classificações concorrentes do mesmo documento."""
    Document.objects.select_for_update().get(pk=document.pk)
    return (
        DocumentClassification.objects.select_related("ledger_account")
        .filter(document=document)
        .first()
    )


def classify_document(
    document: Document, condominium: Condominium
) -> DocumentClassification | None:
    """Roda o motor e registra o resultado. Devolve a classificação vigente.

    A escolha manual do operador nunca é trocada: a sugestão do motor só vira
    evento (`applied=False`). Sem regra aplicável, o estado também não muda.
    """
    result = classify(facts_for_document(document), condominium)

    with transaction.atomic():
        current = _lock(document)
        previous = current.ledger_account if current else None
        manual_wins = (
            current is not None
            and current.origin == DocumentClassification.Origin.MANUAL
        )
        applied = result is not None and not manual_wins

        if applied:
            current, _ = DocumentClassification.objects.update_or_create(
                document=document,
                defaults={
                    "ledger_account": result.ledger_account,
                    "origin": DocumentClassification.Origin.AUTOMATIC,
                    "rule_id": result.rule_id,
                    "reason": result.reason[:255],
                    "classified_by": None,
                },
            )

        _record_classification_event(
            document,
            DocumentClassifiedData(
                origin="automatic",
                applied=applied,
                ledger_account=_ref(result.ledger_account) if result else None,
                previous_ledger_account=_ref(previous),
                rule_id=result.rule_id if result else "",
                reason=result.reason if result else NO_RULE_REASON,
            ),
        )
        return current


def set_manual_classification(
    document: Document, ledger_account: LedgerAccount, user: AbstractBaseUser
) -> DocumentClassification:
    """Operador escolhe a conta. Substitui a vigente e registra de/para no evento."""
    with transaction.atomic():
        current = _lock(document)
        previous = current.ledger_account if current else None
        classification, _ = DocumentClassification.objects.update_or_create(
            document=document,
            defaults={
                "ledger_account": ledger_account,
                "origin": DocumentClassification.Origin.MANUAL,
                "rule_id": "",
                "reason": "",
                "classified_by": user,
            },
        )
        _record_classification_event(
            document,
            DocumentClassifiedData(
                origin="manual",
                applied=True,
                ledger_account=_ref(ledger_account),
                previous_ledger_account=_ref(previous),
                classified_by=user.get_username(),
            ),
        )
        return classification
