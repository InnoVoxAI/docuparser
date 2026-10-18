"""Compara o que veio da fonte com o que já existe e decide as propostas.

Funções puras: recebem objetos normalizados da fonte e um retrato do estado local,
e devolvem rascunhos de proposta. Nada aqui lê ou grava no banco.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Any

from condominiums.text import normalize_text

from erp_import.sources.base import SourceAccount, SourceChart, SourceCondominium

# Entidades e ações (espelham os choices de `ImportProposal`).
CONDOMINIUM, CHART, ACCOUNT = "condominium", "chart", "account"
NEW, UPDATE, DEACTIVATE, CONFLICT = "new", "update", "deactivate", "conflict"

# Tipos de conflito (`data["conflict_kind"]`).
CNPJ_DUPLICATED = "cnpj_duplicated"
CNPJ_TAKEN_LOCALLY = "cnpj_taken_locally"


@dataclass(frozen=True)
class LocalCondominium:
    external_id: str
    name: str
    cnpj: str
    is_active: bool
    chart_external_id: str


@dataclass(frozen=True)
class LocalChart:
    external_id: str
    name: str
    is_active: bool


@dataclass(frozen=True)
class LocalAccount:
    name: str
    is_active: bool


@dataclass(frozen=True)
class LocalState:
    condominiums: dict[str, LocalCondominium] = field(default_factory=dict)
    # CNPJ -> id externo do condomínio que o tem; "" quando o cadastro não veio da fonte.
    cnpj_owners: dict[str, str] = field(default_factory=dict)
    charts: dict[str, LocalChart] = field(default_factory=dict)
    # (id externo do plano, código da conta) -> conta.
    accounts: dict[tuple[str, str], LocalAccount] = field(default_factory=dict)


@dataclass(frozen=True)
class ProposalDraft:
    entity_type: str
    external_id: str
    action: str
    data: dict[str, Any]
    diff: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


def account_key(chart_external_id: str, code: str) -> str:
    return f"{chart_external_id}/{code}"


def _identity(condominium: SourceCondominium) -> tuple[str, str]:
    return (normalize_text(condominium.name), normalize_text(condominium.address))


def _condominium_data(condominium: SourceCondominium) -> dict[str, Any]:
    return {
        "name": condominium.name,
        "cnpj": condominium.cnpj,
        "is_active": condominium.is_active,
        "chart_external_id": condominium.chart_external_id,
        "address": condominium.address,
    }


def _prefer(records: list[SourceCondominium], known: set[str]) -> SourceCondominium:
    """Entre registros do mesmo condomínio, fica o ativo; depois o já importado."""
    return min(records, key=lambda r: (not r.is_active, r.external_id not in known))


def _diff(pairs: Iterable[tuple[str, Any, Any]]) -> dict[str, dict[str, Any]]:
    return {name: {"from": old, "to": new} for name, old, new in pairs if old != new}


def plan_condominiums(
    source: list[SourceCondominium],
    local: LocalState,
    administrator_cnpj: str = "",
) -> list[ProposalDraft]:
    known = set(local.condominiums)
    warnings: dict[str, list[str]] = {}

    def warn(external_id: str, code: str) -> None:
        warnings.setdefault(external_id, []).append(code)

    cleaned: list[SourceCondominium] = []
    for record in source:
        if record.cnpj_invalid:
            warn(record.external_id, "cnpj_invalid")
        if administrator_cnpj and record.cnpj == administrator_cnpj:
            record = replace(record, cnpj="")
            warn(record.external_id, "administrator_cnpj")
        cleaned.append(record)

    # Condomínio inativo na fonte só entra se já for conhecido.
    def importable(record: SourceCondominium) -> bool:
        return record.is_active or record.external_id in known

    kept: dict[str, SourceCondominium] = {
        r.external_id: r for r in cleaned if importable(r)
    }
    duplicates: dict[str, list[str]] = {}
    conflicts: dict[str, list[SourceCondominium]] = {}
    by_cnpj: dict[str, list[SourceCondominium]] = {}
    for record in cleaned:
        if record.cnpj:
            by_cnpj.setdefault(record.cnpj, []).append(record)

    for cnpj, group in by_cnpj.items():
        by_identity: dict[tuple[str, str], list[SourceCondominium]] = {}
        for record in group:
            by_identity.setdefault(_identity(record), []).append(record)

        # Mesmo nome e endereço é o mesmo condomínio cadastrado mais de uma vez.
        representatives = []
        for records in by_identity.values():
            winner = _prefer(records, known)
            if importable(winner):
                representatives.append(winner)
            for other in records:
                if other.external_id != winner.external_id:
                    if importable(winner):
                        duplicates.setdefault(winner.external_id, []).append(
                            other.external_id
                        )
                    kept.pop(other.external_id, None)
                    warnings.pop(other.external_id, None)
        if len(representatives) < 2:
            continue

        # Nomes ou endereços diferentes: o CNPJ não é confiável. Se um deles já o
        # tem no cadastro, o operador já decidiu e os outros entram sem CNPJ.
        owner = local.cnpj_owners.get(cnpj, "")
        decided = any(r.external_id == owner for r in representatives)
        for record in representatives:
            kept[record.external_id] = replace(record, cnpj="")
            warn(record.external_id, "cnpj_conflict")
            if not decided:
                conflicts[record.external_id] = representatives

    drafts: list[ProposalDraft] = []
    for external_id, record in kept.items():
        extra = tuple(warnings.get(external_id, ()))
        data = _condominium_data(record)
        if external_id in duplicates:
            data["duplicate_external_ids"] = sorted(duplicates[external_id])
        current = local.condominiums.get(external_id)

        if external_id in conflicts:
            data["conflict_kind"] = CNPJ_DUPLICATED
            # O CNPJ original: a proposta entra sem ele, e o operador pode atribuí-lo.
            data["source_cnpj"] = next(
                r.cnpj for r in conflicts[external_id] if r.external_id == external_id
            )
            data["cnpj_candidates"] = [
                {"external_id": r.external_id, "name": r.name, "address": r.address}
                for r in conflicts[external_id]
            ]
            drafts.append(
                ProposalDraft(CONDOMINIUM, external_id, CONFLICT, data, {}, extra)
            )
            continue

        owner = local.cnpj_owners.get(record.cnpj) if record.cnpj else None
        if record.cnpj and owner is not None and owner != external_id:
            data["conflict_kind"] = CNPJ_TAKEN_LOCALLY
            drafts.append(
                ProposalDraft(CONDOMINIUM, external_id, CONFLICT, data, {}, extra)
            )
            continue

        if current is None:
            drafts.append(ProposalDraft(CONDOMINIUM, external_id, NEW, data, {}, extra))
            continue

        diff = _diff(
            [
                ("name", current.name, record.name),
                ("is_active", current.is_active, record.is_active),
                (
                    "chart_external_id",
                    current.chart_external_id,
                    record.chart_external_id,
                ),
            ]
        )
        # CNPJ vazio na fonte (ou descartado por desconfiança) nunca apaga o local.
        if record.cnpj and record.cnpj != current.cnpj:
            diff["cnpj"] = {"from": current.cnpj, "to": record.cnpj}
        if diff:
            drafts.append(
                ProposalDraft(CONDOMINIUM, external_id, UPDATE, data, diff, extra)
            )

    # Sumiu da fonte, ou virou duplicado de outro registro: desativa, nunca apaga.
    present = {r.external_id for r in source}
    duplicate_ids = {d for ids in duplicates.values() for d in ids}
    for external_id, current in local.condominiums.items():
        vanished = external_id not in present
        if current.is_active and (vanished or external_id in duplicate_ids):
            drafts.append(
                ProposalDraft(
                    CONDOMINIUM,
                    external_id,
                    DEACTIVATE,
                    {"name": current.name},
                    {"is_active": {"from": True, "to": False}},
                    () if vanished else ("duplicate",),
                )
            )
    return drafts


def _account_data(account: SourceAccount) -> dict[str, Any]:
    return {
        "code": account.code,
        "name": account.name,
        "parent_code": account.parent_code,
        "orphan": account.orphan,
    }


def plan_charts(
    charts: list[SourceChart],
    accounts: dict[str, list[SourceAccount]],
    local: LocalState,
) -> list[ProposalDraft]:
    """Planos e contas. Natureza e regras de fornecedor nunca entram na proposta."""
    drafts: list[ProposalDraft] = []
    present = {c.external_id for c in charts}

    for chart in charts:
        current = local.charts.get(chart.external_id)
        source_accounts = accounts.get(chart.external_id, [])
        warnings = (
            ("orphan_accounts",) if any(a.orphan for a in source_accounts) else ()
        )

        if current is None:
            # O plano novo leva as contas junto: elas só existem depois de aprovado.
            data = {
                "name": chart.name,
                "accounts": [_account_data(a) for a in source_accounts],
            }
            drafts.append(
                ProposalDraft(CHART, chart.external_id, NEW, data, {}, warnings)
            )
            continue

        diff = _diff([("name", current.name, chart.name)])
        if not current.is_active:
            diff["is_active"] = {"from": False, "to": True}
        if diff:
            drafts.append(
                ProposalDraft(
                    CHART, chart.external_id, UPDATE, {"name": chart.name}, diff
                )
            )

        seen = set()
        for account in source_accounts:
            seen.add(account.code)
            key = account_key(chart.external_id, account.code)
            existing = local.accounts.get((chart.external_id, account.code))
            data = _account_data(account) | {"chart_external_id": chart.external_id}
            account_warnings = ("orphan",) if account.orphan else ()
            if existing is None:
                drafts.append(
                    ProposalDraft(ACCOUNT, key, NEW, data, {}, account_warnings)
                )
                continue
            diff = _diff([("name", existing.name, account.name)])
            if not existing.is_active:
                diff["is_active"] = {"from": False, "to": True}
            if diff:
                drafts.append(
                    ProposalDraft(ACCOUNT, key, UPDATE, data, diff, account_warnings)
                )

        for (chart_external_id, code), existing in local.accounts.items():
            if (
                chart_external_id == chart.external_id
                and code not in seen
                and existing.is_active
            ):
                drafts.append(
                    ProposalDraft(
                        ACCOUNT,
                        account_key(chart_external_id, code),
                        DEACTIVATE,
                        {
                            "code": code,
                            "name": existing.name,
                            "chart_external_id": chart_external_id,
                        },
                        {"is_active": {"from": True, "to": False}},
                    )
                )

    for external_id, current in local.charts.items():
        if current.is_active and external_id not in present:
            drafts.append(
                ProposalDraft(
                    CHART,
                    external_id,
                    DEACTIVATE,
                    {"name": current.name},
                    {"is_active": {"from": True, "to": False}},
                )
            )
    return drafts
