"""Identificação do condomínio e classificação do documento, com auditoria.

O estado atual fica em `Document.condominium` e `DocumentClassification`; o histórico,
nos `DocumentEvent` `document.condominium_identified` e `document.classified`.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from condominiums.models import Condominium
from django.contrib.auth.models import AbstractBaseUser
from django.db import connection, transaction
from documents.models import Document, DocumentEvent, ExtractionResult
from documents.services.field_versioning import get_active_version
from docuparse_storage import get_storage
from events import CondominiumIdentifiedEvent, DocumentClassifiedEvent
from events.schemas import (
    CondominiumIdentifiedData,
    CondominiumRef,
    DocumentClassifiedData,
    LedgerAccountRef,
)

from accounting.classification import DocumentFacts, classify
from accounting.classification.identification import identify_condominium
from accounting.models import DocumentClassification, LedgerAccount

logger = logging.getLogger(__name__)

EVENT_SOURCE = "backend-core"
NO_RULE_REASON = "nenhuma regra encontrou conta"
STALE_ACCOUNT_REASON = "conta anterior removida: pertence a outro plano de contas"
NO_CONDOMINIUM_REASON = "nenhum condomínio reconhecido no documento"


def _plain_fields(document: Document) -> dict[str, Any]:
    """Campos extraídos como valores simples (o campo pode vir como {value, confidence})."""
    # Consulta direto: o objeto do pipeline pode trazer a extração anterior em cache.
    version = get_active_version(document)
    extraction = ExtractionResult.objects.filter(document=document).first()
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


def _account_ref(account: LedgerAccount | None) -> LedgerAccountRef | None:
    if account is None:
        return None
    return LedgerAccountRef(id=account.id, code=account.code, name=account.name)


def _condominium_ref(condominium: Condominium | None) -> CondominiumRef | None:
    if condominium is None:
        return None
    return CondominiumRef(
        id=condominium.id, name=condominium.name, cnpj=condominium.cnpj
    )


def _record_event(
    document: Document,
    event_class: type[CondominiumIdentifiedEvent] | type[DocumentClassifiedEvent],
    data: CondominiumIdentifiedData | DocumentClassifiedData,
) -> DocumentEvent:
    tenant = connection.tenant
    event = event_class(
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


def _lock_document(document: Document) -> Document:
    """Serializa alterações concorrentes do mesmo documento."""
    # `of=("self",)`: o Postgres não trava o lado anulável do join com o condomínio.
    return (
        Document.objects.select_for_update(of=("self",))
        .select_related("condominium")
        .get(pk=document.pk)
    )


def _current_classification(document: Document) -> DocumentClassification | None:
    return (
        DocumentClassification.objects.select_related("ledger_account")
        .filter(document=document)
        .first()
    )


def identify_document_condominium(
    document: Document, facts: DocumentFacts
) -> Condominium | None:
    """Preenche o condomínio do documento se ainda estiver em branco.

    Só preenche o que está vazio, então nunca desfaz uma escolha do operador.
    Tenant sem condomínios ativos não usa o plano de contas: nada é feito nem
    registrado. Devolve o condomínio vigente do documento.
    """
    with transaction.atomic():
        locked = _lock_document(document)
        if locked.condominium is not None:
            document.condominium = locked.condominium
            return locked.condominium

        condominiums = list(Condominium.objects.filter(is_active=True))
        if not condominiums:
            return None

        found = identify_condominium(facts, condominiums)
        if found is not None:
            locked.condominium = found.condominium
            locked.save(update_fields=["condominium", "updated_at"])
            document.condominium = found.condominium
        _record_event(
            document,
            CondominiumIdentifiedEvent,
            CondominiumIdentifiedData(
                origin="automatic",
                applied=found is not None,
                method=found.method if found else None,
                condominium=_condominium_ref(found.condominium) if found else None,
                reason=found.reason if found else NO_CONDOMINIUM_REASON,
            ),
        )
        return found.condominium if found else None


def set_document_condominium(
    document: Document, condominium: Condominium, user: AbstractBaseUser
) -> None:
    """Operador define ou corrige o condomínio do documento."""
    with transaction.atomic():
        locked = _lock_document(document)
        previous = locked.condominium
        locked.condominium = condominium
        locked.save(update_fields=["condominium", "updated_at"])
        document.condominium = condominium
        _record_event(
            document,
            CondominiumIdentifiedEvent,
            CondominiumIdentifiedData(
                origin="manual",
                applied=True,
                method="manual",
                condominium=_condominium_ref(condominium),
                previous_condominium=_condominium_ref(previous),
                identified_by=user.get_username(),
            ),
        )


def classify_document(
    document: Document,
    condominium: Condominium,
    facts: DocumentFacts | None = None,
) -> DocumentClassification | None:
    """Roda o motor e registra o resultado. Devolve a classificação vigente.

    A escolha manual do operador nunca é trocada: a sugestão do motor só vira
    evento (`applied=False`). Sem regra aplicável, o estado também não muda,
    exceto quando a conta vigente é de outro condomínio (o documento trocou de
    condomínio com outro plano): essa conta não vale mais e é removida.
    """
    result = classify(facts or facts_for_document(document), condominium)

    with transaction.atomic():
        Document.objects.select_for_update().get(pk=document.pk)
        current = _current_classification(document)
        previous = current.ledger_account if current else None
        stale = (
            previous is not None
            and previous.chart_id != condominium.chart_of_accounts_id
        )
        manual_wins = (
            current is not None
            and not stale
            and current.origin == DocumentClassification.Origin.MANUAL
        )
        applied = result is not None and not manual_wins
        reason = result.reason if result else NO_RULE_REASON

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
        elif stale:
            current.delete()
            current, applied, reason = None, True, STALE_ACCOUNT_REASON

        _record_event(
            document,
            DocumentClassifiedEvent,
            DocumentClassifiedData(
                origin="automatic",
                applied=applied,
                ledger_account=_account_ref(result.ledger_account) if result else None,
                previous_ledger_account=_account_ref(previous),
                rule_id=result.rule_id if result else "",
                reason=reason,
            ),
        )
        return current


def set_manual_classification(
    document: Document, ledger_account: LedgerAccount, user: AbstractBaseUser
) -> DocumentClassification:
    """Operador escolhe a conta. Substitui a vigente e registra de/para no evento."""
    with transaction.atomic():
        Document.objects.select_for_update().get(pk=document.pk)
        current = _current_classification(document)
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
        _record_event(
            document,
            DocumentClassifiedEvent,
            DocumentClassifiedData(
                origin="manual",
                applied=True,
                ledger_account=_account_ref(ledger_account),
                previous_ledger_account=_account_ref(previous),
                classified_by=user.get_username(),
            ),
        )
        return classification


def run_classification(document: Document) -> DocumentClassification | None:
    """Identifica o condomínio (se faltar) e classifica o documento na conta dele."""
    facts = facts_for_document(document)
    condominium = identify_document_condominium(document, facts)
    if condominium is None:
        return None
    return classify_document(document, condominium, facts)


def run_classification_safely(document: Document) -> DocumentClassification | None:
    """Versão para o pipeline: a classificação nunca derruba o processamento."""
    try:
        return run_classification(document)
    except Exception:
        logger.error(
            "classification_failed",
            exc_info=True,
            extra={"document_id": str(document.id)},
        )
        return None
