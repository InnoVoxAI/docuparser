"""Fluxo do analista para o lançamento no ERP: confirmar, reenviar e ver o estado.

Em `sandbox` e `live` a aprovação do documento não envia nada: o analista vê o resumo
do que será lançado e confirma. Em `mock` e `disabled` o comportamento de sempre
continua (a aprovação já pede a integração).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from django.utils import timezone as dj_timezone
from events import ERPSendConfirmedEvent, ERPSendRetriedEvent

from documents.models import Document, DocumentEvent, ERPIntegrationAttempt
from documents.services import erp_retry
from documents.services.erp_publisher import (
    current_integration_settings,
    ensure_pending_confirmation,
    idempotency_key_for,
    publish_erp_integration_requested,
)

Status = ERPIntegrationAttempt.Status
EVENT_SOURCE = "backend-core"

# Estados mostrados ao analista.
STATE_NONE = "none"
STATE_AWAITING = "awaiting_confirmation"
STATE_BLOCKED = "blocked"
STATE_SENDING = "sending"
STATE_SENT = "sent"
STATE_FAILED = "failed"
STATE_DRY_RUN = "dry_run"

_STATE_BY_STATUS = {
    Status.PENDING_CONFIRMATION: STATE_AWAITING,
    Status.REQUESTED: STATE_SENDING,
    Status.SENT: STATE_SENT,
    Status.FAILED: STATE_FAILED,
    Status.DRY_RUN: STATE_DRY_RUN,
}


class ErpFlowError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 409,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.errors = errors or []


def _confirmation_required() -> bool:
    from erp_export.policy import confirmation_required

    return confirmation_required(current_integration_settings())


def prepare_after_approval(document: Document) -> None:
    """Chamado na aprovação. Confirmação exigida: só deixa aguardando; senão, integra."""
    if _confirmation_required():
        ensure_pending_confirmation(document)
        return
    publish_erp_integration_requested(document)


def erp_states_for(document_ids: list) -> dict[Any, str]:
    """Estado do ERP de vários documentos numa consulta só (listagens)."""
    states: dict[Any, str] = {}
    attempts = ERPIntegrationAttempt.objects.filter(document_id__in=document_ids)
    for attempt in attempts.order_by("created_at"):
        states[attempt.document_id] = state_of(attempt)
    return states


def _attempt(document: Document) -> ERPIntegrationAttempt | None:
    return document.erp_attempts.order_by("-created_at").first()


def state_of(attempt: ERPIntegrationAttempt | None) -> str:
    """Estado barato (sem montar a despesa), para listagens."""
    return _STATE_BY_STATUS.get(attempt.status, STATE_NONE) if attempt else STATE_NONE


def _retry_info(attempt: ERPIntegrationAttempt) -> dict[str, Any]:
    payload = attempt.response_payload or {}
    retryable = bool(payload.get("retryable"))
    exhausted = retryable and attempt.retry_count >= erp_retry.MAX_ATTEMPTS
    waiting = (
        retryable
        and not exhausted
        and attempt.next_retry_at is not None
        and attempt.next_retry_at > dj_timezone.now()
    )
    return {
        "retryable": retryable,
        "exhausted": exhausted,
        "can_retry": retryable and not exhausted and not waiting,
        "next_retry_at": attempt.next_retry_at.isoformat()
        if attempt.next_retry_at
        else None,
    }


def _draft_info(
    document: Document,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    from erp_export.draft import build_draft
    from erp_export.errors import DraftInvalid

    try:
        return build_draft(document).summary(), []
    except DraftInvalid as invalid:
        return None, [
            {"code": error.code, "message": error.message} for error in invalid.errors
        ]


def erp_detail(document: Document) -> dict[str, Any]:
    """Estado completo do lançamento, para a tela de detalhe do documento."""
    config = current_integration_settings()
    required = _confirmation_required()
    attempt = _attempt(document)
    state = state_of(attempt)
    approved_without_attempt = (
        attempt is None and document.status == Document.Status.APPROVED and required
    )
    if approved_without_attempt:
        state = STATE_AWAITING

    detail: dict[str, Any] = {
        "state": state,
        "mode": config.superlogica_mode,
        "dry_run": bool(config.superlogica_dry_run),
        "confirmation_required": required,
        "summary": None,
        "errors": [],
        "reason": "",
        "code": "",
        "attempts": attempt.retry_count if attempt else 0,
        "max_attempts": erp_retry.MAX_ATTEMPTS,
        "retryable": False,
        "exhausted": False,
        "can_retry": False,
        "next_retry_at": None,
        "external_id": attempt.external_id if attempt else "",
        "can_confirm": False,
    }
    if state in (STATE_AWAITING, STATE_DRY_RUN, STATE_FAILED):
        detail["summary"], detail["errors"] = _draft_info(document)
        if detail["errors"] and state == STATE_AWAITING:
            detail["state"] = STATE_BLOCKED
    if attempt and attempt.status == Status.FAILED:
        payload = attempt.response_payload or {}
        detail["reason"] = payload.get("reason", "")
        detail["code"] = payload.get("code", "")
        detail.update(_retry_info(attempt))

    detail["can_confirm"] = bool(
        required
        and not detail["errors"]
        and (
            detail["state"] in (STATE_AWAITING, STATE_DRY_RUN)
            or (detail["state"] == STATE_FAILED and not detail["retryable"])
        )
    )
    return detail


def _record_decision(event_class, document: Document, user, attempt) -> None:
    """Grava quem confirmou (ou reenviou) e quando, no histórico do documento."""
    event = event_class(
        tenant_id=_tenant_slug(),
        document_id=document.id,
        correlation_id=document.correlation_id,
        source=EVENT_SOURCE,
        occurred_at=datetime.now(timezone.utc),
        data={
            "idempotency_key": attempt.idempotency_key,
            "connector": attempt.connector or "superlogica",
            "confirmed_by": user.get_username(),
        },
    )
    DocumentEvent.objects.create(
        event_id=event.event_id,
        document=document,
        event_type=event.event_type,
        event_version=event.event_version,
        correlation_id=event.correlation_id,
        source=event.source,
        occurred_at=event.occurred_at,
        payload=event.model_dump(mode="json"),
    )


def _tenant_slug() -> str:
    from django.db import connection

    tenant = getattr(connection, "tenant", None)
    return getattr(tenant, "slug", "") or connection.schema_name


def _require_sendable_document(document: Document) -> None:
    if document.status not in (Document.Status.APPROVED, Document.Status.ERP_FAILED):
        raise ErpFlowError(
            "not_approved",
            "Só um documento aprovado, ou com falha no envio, pode ser enviado ao ERP.",
        )


def confirm_send(document: Document, user) -> dict[str, Any]:
    """O analista confirma o primeiro envio (ou o reenvio depois de corrigir o documento)."""
    if not _confirmation_required():
        raise ErpFlowError(
            "not_required", "Neste modo o envio ao ERP é automático, sem confirmação."
        )
    attempt = _attempt(document)
    if attempt and attempt.status == Status.SENT:
        raise ErpFlowError("already_sent", "Esta despesa já foi enviada ao ERP.")
    if attempt and attempt.status == Status.REQUESTED:
        raise ErpFlowError("in_progress", "O envio ao ERP já está em andamento.")
    if (
        attempt
        and attempt.status == Status.FAILED
        and (attempt.response_payload or {}).get("retryable")
    ):
        raise ErpFlowError(
            "use_retry",
            "Esta falha pode ser repetida: use o reenvio, não a confirmação.",
        )
    _require_sendable_document(document)

    summary, errors = _draft_info(document)
    if errors:
        raise ErpFlowError(
            "invalid",
            "O documento ainda tem pendências para lançar no ERP.",
            status=422,
            errors=errors,
        )
    attempt = ensure_pending_confirmation(document)
    _record_decision(ERPSendConfirmedEvent, document, user, attempt)
    publish_erp_integration_requested(document)
    return erp_detail(Document.objects.get(pk=document.pk))


def retry_send(document: Document, user) -> dict[str, Any]:
    """Reenvio de uma falha retentável, respeitando a espera e o limite de tentativas."""
    attempt = _attempt(document)
    if attempt is None or attempt.status != Status.FAILED:
        raise ErpFlowError("no_failure", "Não há falha de envio para repetir.")
    info = _retry_info(attempt)
    if not info["retryable"]:
        raise ErpFlowError(
            "not_retryable",
            "Esta falha pede correção do documento antes de enviar de novo.",
        )
    if info["exhausted"]:
        raise ErpFlowError(
            "exhausted",
            f"As {erp_retry.MAX_ATTEMPTS} tentativas se esgotaram. Procure o suporte.",
        )
    if not info["can_retry"]:
        raise ErpFlowError(
            "wait",
            "Aguarde um pouco antes de tentar de novo.",
        )
    _require_sendable_document(document)
    _record_decision(ERPSendRetriedEvent, document, user, attempt)
    publish_erp_integration_requested(document)
    return erp_detail(Document.objects.get(pk=document.pk))


__all__ = [
    "ErpFlowError",
    "confirm_send",
    "erp_detail",
    "erp_states_for",
    "idempotency_key_for",
    "prepare_after_approval",
    "retry_send",
    "state_of",
]
