"""Sincronização com a fonte e decisões do operador sobre as propostas.

A sincronização só grava `ImportBatch` e `ImportProposal`. `Condominium`,
`ChartOfAccounts` e `LedgerAccount` só mudam quando uma proposta é aplicada.
"""

from __future__ import annotations

import logging

from accounting.models import ChartOfAccounts, LedgerAccount
from condominiums.models import Condominium
from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.utils import timezone

from erp_import import planning
from erp_import.models import ImportBatch, ImportProposal
from erp_import.planning import LocalState, ProposalDraft
from erp_import.sources.base import RegistrySource, SourceError

logger = logging.getLogger(__name__)

UNEXPECTED_ERROR = "Erro inesperado ao sincronizar. Tente novamente."


class InvalidDecision(Exception):
    """A decisão não cabe no estado ou no tipo da proposta."""


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


def _signature(draft: ProposalDraft) -> tuple:
    return (
        draft.action,
        draft.data,
        draft.diff,
        list(draft.warnings),
    )


def _persist(batch: ImportBatch, drafts: list[ProposalDraft]) -> None:
    """Grava os rascunhos, sem repetir proposta pendente idêntica de lote anterior."""
    open_proposals = {
        (p.entity_type, p.external_id): p
        for p in ImportProposal.objects.filter(status=ImportProposal.Status.PENDING)
    }
    drafted = {(d.entity_type, d.external_id) for d in drafts}
    for key, stale in open_proposals.items():
        if key not in drafted:
            stale.status = ImportProposal.Status.SUPERSEDED
            stale.save(update_fields=["status", "updated_at"])

    for draft in drafts:
        previous = open_proposals.get((draft.entity_type, draft.external_id))
        if previous is not None:
            same = _signature(draft) == (
                previous.action,
                previous.data,
                previous.diff,
                previous.warnings,
            )
            if same:
                continue
            previous.status = ImportProposal.Status.SUPERSEDED
            previous.save(update_fields=["status", "updated_at"])
        ImportProposal.objects.create(
            batch=batch,
            entity_type=draft.entity_type,
            external_id=draft.external_id,
            action=draft.action,
            data=draft.data,
            diff=draft.diff,
            warnings=list(draft.warnings),
        )


def run_sync(
    source: RegistrySource,
    user: AbstractBaseUser | None,
    administrator_cnpj: str = "",
) -> ImportBatch:
    """Lê a fonte e grava as propostas. Falha na fonte deixa o lote em erro, sem propostas."""
    batch = ImportBatch.objects.create(
        source=source.source_name, started_by=user, status=ImportBatch.Status.RUNNING
    )
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


def _decide(
    proposal: ImportProposal,
    user: AbstractBaseUser,
    status: str,
    resolution: dict | None = None,
) -> ImportProposal:
    with transaction.atomic():
        locked = ImportProposal.objects.select_for_update().get(pk=proposal.pk)
        if locked.status != ImportProposal.Status.PENDING:
            raise InvalidDecision("A proposta já foi decidida ou substituída.")
        is_conflict = locked.action == ImportProposal.Action.CONFLICT
        if status == ImportProposal.Status.APPROVED and is_conflict:
            raise InvalidDecision("Conflitos precisam ser resolvidos, não aprovados.")
        if status == ImportProposal.Status.RESOLVED and not is_conflict:
            raise InvalidDecision("Só conflitos podem ser resolvidos.")
        locked.status = status
        locked.resolution = resolution or {}
        locked.decided_by = user
        locked.decided_at = timezone.now()
        locked.save()
        return locked


def approve(proposal: ImportProposal, user: AbstractBaseUser) -> ImportProposal:
    return _decide(proposal, user, ImportProposal.Status.APPROVED)


def reject(proposal: ImportProposal, user: AbstractBaseUser) -> ImportProposal:
    return _decide(proposal, user, ImportProposal.Status.REJECTED)


def resolve(
    proposal: ImportProposal, user: AbstractBaseUser, resolution: dict
) -> ImportProposal:
    """Operador resolve um conflito; `resolution` depende do tipo (`data["conflict_kind"]`)."""
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
    return _decide(proposal, user, ImportProposal.Status.RESOLVED, resolution)
