"""Consultas ao Superlógica antes de lançar: fornecedor e despesa já existente.

Só usa o `SuperlogicaClient`, que faz apenas GET. O formato da resposta de
`despesas` (id, CNPJ do recebedor, apropriações, datas) é o que a importação já lê e
foi verificado; o de fornecedores é hipótese (ver `payload.py`).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from condominiums.tax_ids import normalize_tax_id

from erp_export import payload
from erp_export.draft import ExpenseDraft, parse_date
from erp_export.errors import ExportError

PAGE_SIZE = 50
MAX_PAGES = 20
# Folga ao redor das datas da despesa ao procurar uma já lançada.
SEARCH_MARGIN_DAYS = 45
_ONE_CENT = Decimal("0.01")


class Reader(Protocol):
    def get(self, path: str, params: dict[str, Any] | None = None) -> list[Any]: ...


def _text(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    return str(value).strip() if value not in (None, "") else ""


def resolve_supplier_id(reader: Reader, tax_id: str) -> str:
    """Id do fornecedor no ERP pelo CNPJ ou CPF. Sem cadastro, o analista é avisado."""
    rows = reader.get(
        payload.SUPPLIER_LIST_PATH, {payload.SUPPLIER_SEARCH_PARAM: tax_id}
    )
    for row in rows:
        for key in payload.SUPPLIER_TAX_ID_KEYS:
            if normalize_tax_id(_text(row, key)) == tax_id:
                supplier_id = _text(row, payload.SUPPLIER_ID_KEY)
                if supplier_id:
                    return supplier_id
    raise ExportError(
        "supplier_not_found",
        "O fornecedor não está cadastrado no Superlógica. "
        "Cadastre o fornecedor no ERP e envie de novo.",
    )


def _allocated_total(row: dict[str, Any]) -> Decimal:
    total = Decimal("0")
    for allocation in row.get("apropriacao") or []:
        if not isinstance(allocation, dict):
            continue
        try:
            total += Decimal(_text(allocation, "vl_valor_apro") or "0")
        except InvalidOperation:
            continue
    return total


def _expense_dates(row: dict[str, Any]) -> set[date]:
    return {
        parsed
        for key in ("dt_vencimento_pdes", "dt_despesa_des")
        if (parsed := parse_date(_text(row, key))) is not None
    }


def find_existing_expense(reader: Reader, draft: ExpenseDraft) -> str | None:
    """Id da despesa que já parece ser esta: mesmo fornecedor, valor e vencimento.

    Valor e fornecedor iguais sozinhos não bastam (despesa mensal de mesmo valor),
    por isso o vencimento também precisa bater.
    """
    dates = [i.due_date for i in draft.installments]
    start = min(dates) - timedelta(days=SEARCH_MARGIN_DAYS)
    end = max(dates) + timedelta(days=SEARCH_MARGIN_DAYS)
    wanted_dates = set(dates)

    seen: set[str] = set()
    for page in range(1, MAX_PAGES + 1):
        rows = reader.get(
            "despesas",
            {
                "idCondominio": draft.condominium_external_id,
                "dtInicio": start.isoformat(),
                "dtFim": end.isoformat(),
                "itensPorPagina": PAGE_SIZE,
                "pagina": page,
            },
        )
        ids = {_text(row, "id_despesa_des") for row in rows}
        # Página vazia é o fim; página sem id novo indica que a API ignorou `pagina`.
        if not ids - seen:
            return None
        seen |= ids
        for row in rows:
            tax_id = normalize_tax_id(
                _text(row, "st_cpfcnpjrecebedor_con") or _text(row, "st_cpf_con")
            )
            if tax_id != draft.supplier_tax_id:
                continue
            if abs(_allocated_total(row) - draft.amount) > _ONE_CENT:
                continue
            if _expense_dates(row) & wanted_dates:
                return _text(row, "id_despesa_des") or None
    return None
