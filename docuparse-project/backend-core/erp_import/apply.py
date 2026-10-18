"""Aplica uma proposta decidida em `Condominium`, `ChartOfAccounts` e `LedgerAccount`.

Chamado dentro da transação da decisão: qualquer `ApplyError` desfaz a decisão.
Natureza, regras de fornecedor e nomes alternativos nunca são tocados.
"""

from __future__ import annotations

from typing import Any

from accounting.models import ChartOfAccounts, LedgerAccount
from condominiums.models import Condominium
from django.db import IntegrityError, transaction

from erp_import import planning
from erp_import.models import ImportProposal

P = ImportProposal


class InvalidDecision(Exception):
    """A decisão não cabe no estado ou no tipo da proposta. A mensagem é legível."""


class ApplyError(InvalidDecision):
    """A mudança não pode ser aplicada ao cadastro atual."""


def apply_proposal(proposal: ImportProposal) -> None:
    source = proposal.batch.source
    handlers = {
        P.EntityType.CHART: _apply_chart,
        P.EntityType.ACCOUNT: _apply_account,
        P.EntityType.CONDOMINIUM: _apply_condominium,
    }
    try:
        with transaction.atomic():
            handlers[proposal.entity_type](proposal, source)
    except IntegrityError:
        raise ApplyError(
            "A mudança conflita com um cadastro existente (código ou CNPJ já em uso)."
        ) from None


def _set_from_diff(
    obj: Any, diff: dict[str, dict[str, Any]], fields: tuple[str, ...]
) -> None:
    for name in fields:
        if name in diff:
            setattr(obj, name, diff[name]["to"])


def _chart(source: str, external_id: str) -> ChartOfAccounts:
    chart = ChartOfAccounts.objects.filter(
        external_source=source, external_id=external_id
    ).first()
    if chart is None:
        raise ApplyError(
            f"Aprove o plano de contas {external_id} antes dos itens que dependem dele."
        )
    return chart


def _apply_chart(proposal: ImportProposal, source: str) -> None:
    data = proposal.data
    if proposal.action == P.Action.NEW:
        chart, _ = ChartOfAccounts.objects.get_or_create(
            external_source=source,
            external_id=proposal.external_id,
            defaults={"name": data["name"]},
        )
        _create_accounts(chart, data.get("accounts", []))
        return
    chart = _chart(source, proposal.external_id)
    if proposal.action == P.Action.DEACTIVATE:
        chart.is_active = False
    else:
        _set_from_diff(chart, proposal.diff, ("name", "is_active"))
    chart.save()


def _create_accounts(chart: ChartOfAccounts, accounts: list[dict[str, Any]]) -> None:
    """Cria as contas do plano novo, pais antes dos filhos (pelo código pontuado)."""
    by_code = {a.code: a for a in LedgerAccount.objects.filter(chart=chart)}
    for item in sorted(accounts, key=lambda a: a["code"].count(".")):
        if item["code"] in by_code:
            continue
        parent = by_code.get(item["parent_code"]) if item["parent_code"] else None
        by_code[item["code"]] = LedgerAccount.objects.create(
            chart=chart, code=item["code"], name=item["name"], parent=parent
        )


def _apply_account(proposal: ImportProposal, source: str) -> None:
    data = proposal.data
    chart = _chart(source, data["chart_external_id"])
    if proposal.action == P.Action.NEW:
        parent = (
            LedgerAccount.objects.filter(chart=chart, code=data["parent_code"]).first()
            if data.get("parent_code")
            else None
        )
        LedgerAccount.objects.update_or_create(
            chart=chart,
            code=data["code"],
            defaults={"name": data["name"], "is_active": True, "parent": parent},
        )
        return
    account = LedgerAccount.objects.filter(chart=chart, code=data["code"]).first()
    if account is None:
        raise ApplyError(f"A conta {data['code']} não existe mais no plano.")
    if proposal.action == P.Action.DEACTIVATE:
        account.is_active = False
    else:
        _set_from_diff(account, proposal.diff, ("name", "is_active"))
    account.save()


def _condominium(source: str, external_id: str) -> Condominium | None:
    return Condominium.objects.filter(
        external_source=source, external_id=external_id
    ).first()


def _chart_or_none(source: str, chart_external_id: str) -> ChartOfAccounts | None:
    return _chart(source, chart_external_id) if chart_external_id else None


def _assign_chart(condominium: Condominium, chart: ChartOfAccounts | None) -> None:
    if chart != condominium.chart_of_accounts:
        if condominium.pk and condominium.supplier_rules.exists():
            raise ApplyError(
                "Remova as regras de fornecedor antes de trocar o plano de contas."
            )
        condominium.chart_of_accounts = chart


def _assign_cnpj(condominium: Condominium, cnpj: str) -> None:
    """CNPJ vazio nunca apaga o que o cadastro já tem."""
    if not cnpj or cnpj == condominium.cnpj:
        return
    taken = Condominium.objects.filter(cnpj=cnpj).exclude(pk=condominium.pk)
    if taken.exists():
        raise ApplyError(f"Já existe um condomínio com o CNPJ {cnpj}.")
    condominium.cnpj = cnpj


def _upsert_condominium(proposal: ImportProposal, source: str, cnpj: str) -> None:
    data = proposal.data
    condominium = _condominium(source, proposal.external_id) or Condominium(
        external_source=source, external_id=proposal.external_id
    )
    condominium.name = data["name"]
    condominium.is_active = data["is_active"]
    _assign_chart(condominium, _chart_or_none(source, data["chart_external_id"]))
    _assign_cnpj(condominium, cnpj)
    condominium.save()


def _apply_condominium(proposal: ImportProposal, source: str) -> None:
    data = proposal.data
    if proposal.action == P.Action.NEW:
        _upsert_condominium(proposal, source, data["cnpj"])
        return
    if proposal.action == P.Action.CONFLICT:
        _apply_condominium_conflict(proposal, source)
        return

    condominium = _condominium(source, proposal.external_id)
    if condominium is None:
        raise ApplyError("O condomínio não existe mais no cadastro.")
    if proposal.action == P.Action.DEACTIVATE:
        condominium.is_active = False
        condominium.save()
        return
    _set_from_diff(condominium, proposal.diff, ("name", "is_active"))
    if "chart_external_id" in proposal.diff:
        chart_id = proposal.diff["chart_external_id"]["to"]
        _assign_chart(condominium, _chart_or_none(source, chart_id))
    if "cnpj" in proposal.diff:
        _assign_cnpj(condominium, proposal.diff["cnpj"]["to"])
    condominium.save()


def _apply_condominium_conflict(proposal: ImportProposal, source: str) -> None:
    data, resolution = proposal.data, proposal.resolution
    kind = data.get("conflict_kind")

    if kind == planning.CNPJ_DUPLICATED:
        keeps_cnpj = resolution["cnpj_owner"] == proposal.external_id
        _upsert_condominium(proposal, source, data["source_cnpj"] if keeps_cnpj else "")
        return

    if kind == planning.CNPJ_TAKEN_LOCALLY:
        if not resolution["link_to_local"]:
            _upsert_condominium(proposal, source, "")
            return
        local = Condominium.objects.filter(cnpj=data["cnpj"]).first()
        if local is None:
            raise ApplyError("O cadastro local com este CNPJ não existe mais.")
        if _condominium(source, proposal.external_id) not in (None, local):
            raise ApplyError("Este condomínio já está ligado a outro cadastro.")
        local.external_source, local.external_id = source, proposal.external_id
        local.name = data["name"]
        local.is_active = data["is_active"]
        _assign_chart(local, _chart_or_none(source, data["chart_external_id"]))
        local.save()
        return

    raise ApplyError("Conflito de tipo desconhecido.")
