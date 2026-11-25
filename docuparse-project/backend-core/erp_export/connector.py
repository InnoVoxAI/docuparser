"""Conector do Superlógica: executa um pedido de lançamento (`erp.integration.requested`).

Ordem de segurança, da mais barata à que fala com o ERP:

1. política (modo, dry-run, host, habilitação): decide se pode haver envio;
2. montagem e validação da despesa (sem rede);
3. dry-run: registra o que seria enviado e para;
4. credenciais e fornecedor (só leitura no ERP);
5. consulta de duplicidade (só leitura no ERP);
6. marca "envio iniciado" no banco e só então faz o POST.

O passo 6 deixa o rastro que permite reconciliar uma resposta perdida: na próxima
tentativa o passo 5 acha a despesa no ERP e o conector marca como enviada, sem reenviar.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from django.utils import timezone
from documents.models import (
    SETTINGS_SINGLETON_ID,
    Document,
    ERPIntegrationAttempt,
    IntegrationSettings,
)
from documents.services.erp_retry import FINGERPRINT_KEY, STARTED_KEY
from erp_import.credentials import (
    CredentialsError,
    SuperlogicaTokens,
    load_superlogica_tokens,
)
from erp_import.sources.base import SourceAuthError, SourceError
from erp_import.sources.superlogica import SuperlogicaClient

from erp_export import payload as contract
from erp_export.draft import ExpenseDraft, build_draft
from erp_export.errors import DraftInvalid, ExportError
from erp_export.lookup import Reader, find_existing_expense, resolve_supplier_id
from erp_export.policy import WritePolicy, evaluate_policy
from erp_export.writer import SuperlogicaWriter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConnectorResult:
    # sent | failed | dry_run | mock | ignored
    kind: str
    external_id: str = ""
    error: ExportError | None = None
    reconciled: bool = False
    detail: dict[str, Any] = field(default_factory=dict)


ReaderFactory = Callable[[SuperlogicaTokens, str], Reader]
WriterFactory = Callable[[SuperlogicaTokens, str], SuperlogicaWriter]


def _default_reader(tokens: SuperlogicaTokens, base_url: str) -> Reader:
    return SuperlogicaClient(tokens.app_token, tokens.access_token, base_url)


def _default_writer(tokens: SuperlogicaTokens, base_url: str) -> SuperlogicaWriter:
    return SuperlogicaWriter(tokens.app_token, tokens.access_token, base_url)


def _failed(error: ExportError) -> ConnectorResult:
    return ConnectorResult("failed", error=error)


def _save_attempt(attempt: ERPIntegrationAttempt, **changes: Any) -> None:
    for name, value in changes.items():
        setattr(attempt, name, value)
    attempt.save(update_fields=[*changes, "updated_at"])


def _mark_started(attempt: ERPIntegrationAttempt, fingerprint: str) -> None:
    payload = dict(attempt.response_payload or {})
    payload[STARTED_KEY] = timezone.now().isoformat()
    payload[FINGERPRINT_KEY] = fingerprint
    _save_attempt(attempt, response_payload=payload)


def _clear_started(attempt: ERPIntegrationAttempt) -> None:
    payload = dict(attempt.response_payload or {})
    had_marker = payload.pop(STARTED_KEY, None) is not None
    payload.pop(FINGERPRINT_KEY, None)
    if had_marker:
        _save_attempt(attempt, response_payload=payload)


def _dry_run(attempt: ERPIntegrationAttempt, draft: ExpenseDraft) -> ConnectorResult:
    # Monta o corpo só para provar que o mapeamento não quebra; ele não é guardado.
    contract.build_expense_body(draft, supplier_id="dry-run")
    preview = draft.summary()
    _save_attempt(
        attempt,
        status=ERPIntegrationAttempt.Status.DRY_RUN,
        response_payload={"dry_run": True, "preview": preview},
    )
    return ConnectorResult("dry_run", detail={"preview": preview})


def _send(
    attempt: ERPIntegrationAttempt,
    draft: ExpenseDraft,
    policy: WritePolicy,
    reader_factory: ReaderFactory,
    writer_factory: WriterFactory,
) -> ConnectorResult:
    try:
        tokens = load_superlogica_tokens()
    except CredentialsError as exc:
        return _failed(ExportError("credentials_missing", str(exc)))

    try:
        reader = reader_factory(tokens, policy.base_url)
        supplier_id = resolve_supplier_id(reader, draft.supplier_tax_id)
        existing_id = find_existing_expense(reader, draft)
    except ExportError as error:
        return _failed(error)
    except SourceAuthError as exc:
        return _failed(ExportError("auth_rejected", str(exc)))
    except SourceError as exc:
        return _failed(
            ExportError(
                "erp_lookup_failed",
                f"Não foi possível consultar o Superlógica antes de lançar: {exc}",
                retryable=True,
            )
        )

    reconciling = STARTED_KEY in (attempt.response_payload or {})
    if existing_id:
        if reconciling:
            # O envio anterior foi aceito, só a resposta se perdeu: não reenviar.
            return ConnectorResult("sent", external_id=existing_id, reconciled=True)
        return _failed(
            ExportError(
                "duplicate_in_erp",
                "O Superlógica já tem uma despesa com o mesmo fornecedor, valor e "
                f"vencimento (id {existing_id}). Confira no ERP antes de lançar de novo.",
            )
        )

    if reconciling:
        sent_before = (attempt.response_payload or {}).get(FINGERPRINT_KEY)
        if sent_before and sent_before != draft.fingerprint():
            # Um envio ficou sem resposta e o documento mudou depois: a consulta usa os
            # dados novos e não acha a despesa antiga que o ERP pode ter aceito.
            _clear_started(attempt)
            return _failed(
                ExportError(
                    "changed_after_unknown_send",
                    "O documento mudou depois de um envio que ficou sem resposta. Confira "
                    "no Superlógica se a despesa anterior foi lançada, ajuste lá se for "
                    "preciso e só então envie de novo.",
                )
            )

    body = contract.build_expense_body(draft, supplier_id)
    _mark_started(attempt, draft.fingerprint())
    writer = writer_factory(tokens, policy.base_url)
    try:
        result = writer.post(contract.EXPENSE_PATH, body)
    except ExportError as error:
        if not error.outcome_unknown:
            _clear_started(attempt)
        return _failed(error)
    return ConnectorResult("sent", external_id=result.external_id)


def execute(
    document_id: Any,
    idempotency_key: str,
    *,
    reader_factory: ReaderFactory = _default_reader,
    writer_factory: WriterFactory = _default_writer,
) -> ConnectorResult:
    config, _ = IntegrationSettings.objects.get_or_create(id=SETTINGS_SINGLETON_ID)
    policy = evaluate_policy(config)

    if policy.mode == IntegrationSettings.SuperlogicaMode.DISABLED:
        return ConnectorResult("ignored", detail={"reason": "mode_disabled"})
    if policy.mode == IntegrationSettings.SuperlogicaMode.MOCK:
        return ConnectorResult("mock")

    document = Document.objects.get(id=document_id)
    attempt = ERPIntegrationAttempt.objects.get(idempotency_key=idempotency_key)
    try:
        draft = build_draft(document)
    except DraftInvalid as invalid:
        return ConnectorResult(
            "failed",
            error=invalid.errors[0],
            detail={"errors": [error.as_dict() for error in invalid.errors]},
        )

    if policy.dry_run:
        return _dry_run(attempt, draft)
    if not policy.send_allowed:
        return _failed(ExportError("mode_blocked", policy.blocked_reason))
    return _send(attempt, draft, policy, reader_factory, writer_factory)
