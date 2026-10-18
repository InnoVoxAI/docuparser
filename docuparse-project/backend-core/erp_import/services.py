"""Sincronização com a fonte e decisões do operador sobre as propostas.

A sincronização só grava `ImportBatch` e `ImportProposal`. `Condominium`,
`ChartOfAccounts` e `LedgerAccount` só mudam quando uma decisão aplica a proposta.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from accounting.models import ChartOfAccounts, LedgerAccount
from condominiums.models import Condominium
from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.utils import timezone

from erp_import import planning
from erp_import.apply import ApplyError, InvalidDecision, apply_proposal
from erp_import.models import ImportBatch, ImportProposal
from erp_import.planning import LocalState, ProposalDraft
from erp_import.sources.base import RegistrySource, SourceError

logger = logging.getLogger(__name__)

UNEXPECTED_ERROR = "Erro inesperado ao sincronizar. Tente novamente."
STALE_BATCH_ERROR = "A sincronização foi interrompida antes de terminar."
# Um lote "em andamento" há mais tempo que isso é considerado morto.
STALE_AFTER = timedelta(minutes=15)

__all__ = ["ApplyError", "InvalidDecision"]


class SyncInProgress(Exception):
    """Já existe uma sincronização em andamento."""


def load_local_state(source_name: str) -> LocalState:
    condominiums = {}
    cnpj_owners = {}
    for c in Condominium.objects.select_related("chart_of_accounts"):
        linked = c.external_source == source_name and c.external_id
        if c.cnpj:
            cnpj_owners[c.cnpj] = c.external_id if linked else ""
        if linked:
            chart = c.chart_of_accounts
            condominiums[c.external_id] = planning.LocalCondominium(
                external_id=c.external_id,
                name=c.name,
                cnpj=c.cnpj,
                is_active=c.is_active,
                chart_external_id=chart.external_id if chart else "",
            )

    charts = {
        c.external_id: planning.LocalChart(c.external_id, c.name, c.is_active)
        for c in ChartOfAccounts.objects.filter(external_source=source_name).exclude(
            external_id=""
        )
    }
    accounts = {
        (a.chart.external_id, a.code): planning.LocalAccount(a.name, a.is_active)
        for a in LedgerAccount.objects.filter(
            chart__external_source=source_name
        ).select_related("chart")
    }
    return LocalState(condominiums, cnpj_owners, charts, accounts)


def _signature(action: str, data: dict, diff: dict, warnings: list) -> tuple:
    return (action, data, diff, list(warnings))


def _persist(batch: ImportBatch, drafts: list[ProposalDraft]) -> None:
    """Grava os rascunhos, sem repetir o que já está pendente ou foi rejeitado igual."""
    P = ImportProposal
    open_proposals = {
        (p.entity_type, p.external_id): p
        for p in P.objects.filter(status=P.Status.PENDING)
    }
    # Última rejeição de cada entidade: a mesma proposta não volta a cada sincronização.
    rejected = {
        (p.entity_type, p.external_id): p
        for p in P.objects.filter(status=P.Status.REJECTED).order_by("decided_at")
    }

    drafted = {(d.entity_type, d.external_id) for d in drafts}
    for key, stale in open_proposals.items():
        if key not in drafted:
            stale.status = P.Status.SUPERSEDED
            stale.save(update_fields=["status", "updated_at"])

    for draft in drafts:
        key = (draft.entity_type, draft.external_id)
        signature = _signature(draft.action, draft.data, draft.diff, draft.warnings)

        declined = rejected.get(key)
        if declined is not None and signature == _signature(
            declined.action, declined.data, declined.diff, declined.warnings
        ):
            continue

        previous = open_proposals.get(key)
        if previous is not None:
            if signature == _signature(
                previous.action, previous.data, previous.diff, previous.warnings
            ):
                continue
            previous.status = P.Status.SUPERSEDED
            previous.save(update_fields=["status", "updated_at"])
        P.objects.create(
            batch=batch,
            entity_type=draft.entity_type,
            external_id=draft.external_id,
            action=draft.action,
            data=draft.data,
            diff=draft.diff,
            warnings=list(draft.warnings),
        )


def create_batch(source_name: str, user: AbstractBaseUser | None) -> ImportBatch:
    """Abre um lote. Recusa se já houver um em andamento; lote morto é encerrado antes."""
    with transaction.atomic():
        running = ImportBatch.objects.select_for_update().filter(
            status=ImportBatch.Status.RUNNING
        )
        cutoff = timezone.now() - STALE_AFTER
        for stale in running.filter(created_at__lt=cutoff):
            _finish(stale, ImportBatch.Status.ERROR, STALE_BATCH_ERROR)
        if running.filter(created_at__gte=cutoff).exists():
            raise SyncInProgress("Já existe uma sincronização em andamento.")
        return ImportBatch.objects.create(
            source=source_name, started_by=user, status=ImportBatch.Status.RUNNING
        )


def execute_batch(
    batch: ImportBatch, source: RegistrySource, administrator_cnpj: str = ""
) -> ImportBatch:
    """Lê a fonte e grava as propostas. Falha na fonte deixa o lote em erro, sem propostas."""
    try:
        condominiums = source.list_condominiums()
        charts = source.list_charts()
        accounts = {c.external_id: source.list_accounts(c.external_id) for c in charts}
        with transaction.atomic():
            local = load_local_state(source.source_name)
            drafts = planning.plan_condominiums(
                condominiums, local, administrator_cnpj
            ) + planning.plan_charts(charts, accounts, local)
            _persist(batch, drafts)
    except SourceError as exc:
        return _finish(batch, ImportBatch.Status.ERROR, str(exc)[:500])
    except Exception:
        logger.error("import_sync_failed", exc_info=True)
        return _finish(batch, ImportBatch.Status.ERROR, UNEXPECTED_ERROR)
    return _finish(batch, ImportBatch.Status.READY)


def _finish(batch: ImportBatch, status: str, message: str = "") -> ImportBatch:
    batch.status = status
    batch.error_message = message
    batch.finished_at = timezone.now()
    batch.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
    return batch


# Planos antes das contas e dos condomínios que dependem deles.
_APPLY_ORDER = {
    ImportProposal.EntityType.CHART: 0,
    ImportProposal.EntityType.ACCOUNT: 1,
    ImportProposal.EntityType.CONDOMINIUM: 2,
}


def _decide(
    proposal: ImportProposal,
    user: AbstractBaseUser,
    status: str,
    resolution: dict | None = None,
) -> ImportProposal:
    """Registra a decisão e, se aprovada ou resolvida, aplica a mudança na mesma transação."""
    P = ImportProposal
    with transaction.atomic():
        locked = (
            P.objects.select_for_update().select_related("batch").get(pk=proposal.pk)
        )
        if locked.status == status:
            return locked  # repetir a decisão não repete a mudança
        if locked.status != P.Status.PENDING:
            raise InvalidDecision("A proposta já foi decidida ou substituída.")
        is_conflict = locked.action == P.Action.CONFLICT
        if status == P.Status.APPROVED and is_conflict:
            raise InvalidDecision("Conflitos precisam ser resolvidos, não aprovados.")
        if status == P.Status.RESOLVED and not is_conflict:
            raise InvalidDecision("Só conflitos podem ser resolvidos.")

        locked.status = status
        locked.resolution = resolution or {}
        locked.decided_by = user
        locked.decided_at = timezone.now()
        if status in (P.Status.APPROVED, P.Status.RESOLVED):
            apply_proposal(locked)
        locked.save()
        return locked


def approve(proposal: ImportProposal, user: AbstractBaseUser) -> ImportProposal:
    return _decide(proposal, user, ImportProposal.Status.APPROVED)


def reject(proposal: ImportProposal, user: AbstractBaseUser) -> ImportProposal:
    return _decide(proposal, user, ImportProposal.Status.REJECTED)


def _validate_resolution(proposal: ImportProposal, resolution: dict) -> None:
    kind = proposal.data.get("conflict_kind")
    if kind == planning.CNPJ_DUPLICATED:
        allowed = {c["external_id"] for c in proposal.data["cnpj_candidates"]}
        # `cnpj_owner` None: nenhum registro fica com o CNPJ.
        if "cnpj_owner" not in resolution or (
            resolution["cnpj_owner"] is not None
            and resolution["cnpj_owner"] not in allowed
        ):
            raise InvalidDecision("Escolha qual registro fica com o CNPJ, ou nenhum.")
    elif kind == planning.CNPJ_TAKEN_LOCALLY:
        if not isinstance(resolution.get("link_to_local"), bool):
            raise InvalidDecision(
                "Informe se o cadastro local com este CNPJ é o mesmo condomínio."
            )
    else:
        raise InvalidDecision("Conflito de tipo desconhecido.")


def resolve(
    proposal: ImportProposal, user: AbstractBaseUser, resolution: dict
) -> list[ImportProposal]:
    """Operador resolve um conflito. A escolha de CNPJ vale para todos os registros
    do grupo, que são resolvidos juntos."""
    P = ImportProposal
    _validate_resolution(proposal, resolution)
    group = [proposal]
    if proposal.data["conflict_kind"] == planning.CNPJ_DUPLICATED:
        ids = {c["external_id"] for c in proposal.data["cnpj_candidates"]}
        group += [
            p
            for p in P.objects.filter(
                status=P.Status.PENDING,
                action=P.Action.CONFLICT,
                entity_type=P.EntityType.CONDOMINIUM,
            ).exclude(pk=proposal.pk)
            if p.data.get("conflict_kind") == planning.CNPJ_DUPLICATED
            and {c["external_id"] for c in p.data["cnpj_candidates"]} == ids
        ]
    with transaction.atomic():
        return [_decide(p, user, P.Status.RESOLVED, resolution) for p in group]


class BulkResult:
    def __init__(self) -> None:
        self.done: list[ImportProposal] = []
        self.failed: list[tuple[ImportProposal, str]] = []


def decide_many(
    proposals: list[ImportProposal], user: AbstractBaseUser, status: str
) -> BulkResult:
    """Decide as propostas escolhidas, uma transação por proposta, planos primeiro."""
    result = BulkResult()
    for proposal in sorted(proposals, key=lambda p: _APPLY_ORDER[p.entity_type]):
        try:
            result.done.append(_decide(proposal, user, status))
        except InvalidDecision as exc:
            result.failed.append((proposal, str(exc)))
    return result
