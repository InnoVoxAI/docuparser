"""Consultas de leitura ao ERP antes de lançar: fornecedor e despesa já existente."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from erp_import.sources.superlogica import SuperlogicaClient

from erp_export import payload
from erp_export.draft import ExpenseDraft, Installment
from erp_export.errors import ExportError
from erp_export.lookup import find_existing_expense, resolve_supplier_id

from .helpers import (
    CONDOMINIUM_ERP_ID,
    OTHER_CNPJ,
    SUPPLIER_CNPJ,
    FakeResponse,
    FakeSession,
)

DUE = date(2026, 7, 20)


def reader(session: FakeSession) -> SuperlogicaClient:
    return SuperlogicaClient(
        "app",
        "acc",
        "https://sandbox.erp.test/v2/condor",
        session=session,
        pause=0,
        sleep=lambda s: None,
    )


def draft(amount="1000.00", due=DUE, tax_id=SUPPLIER_CNPJ) -> ExpenseDraft:
    return ExpenseDraft(
        document_id="d1",
        kind="boleto",
        condominium_external_id=CONDOMINIUM_ERP_ID,
        condominium_name="Edifício",
        chart_external_id="77",
        account_code="2.1.02",
        account_name="Manutenção",
        supplier_tax_id=tax_id,
        supplier_name="Fornecedor",
        amount=Decimal(amount),
        installments=[Installment(Decimal(amount), due)],
    )


def expense(
    expense_id="1",
    tax_id=SUPPLIER_CNPJ,
    amount="1000.00",
    due="20/07/2026",
    issued="10/07/2026",
):
    return {
        "id_despesa_des": expense_id,
        "st_cpfcnpjrecebedor_con": tax_id,
        "apropriacao": [{"st_conta_cont": "2.1.02", "vl_valor_apro": amount}],
        "dt_vencimento_pdes": due,
        "dt_despesa_des": issued,
    }


def pages(*pages_):
    """Rota de despesas paginada: cada chamada devolve a próxima página; depois, vazio."""
    queue = list(pages_)

    def handler(**kwargs):
        return FakeResponse(200, queue.pop(0) if queue else [])

    return handler


def lookup(rows, **kw):
    session = FakeSession({("GET", "despesas"): pages(rows)})
    return find_existing_expense(reader(session), draft(**kw)), session


def test_supplier_is_resolved_by_tax_id():
    row = {
        payload.SUPPLIER_ID_KEY: "321",
        payload.SUPPLIER_TAX_ID_KEYS[0]: "12.345.678/0001-95",
    }
    session = FakeSession({("GET", "fornecedores"): [row]})
    assert resolve_supplier_id(reader(session), SUPPLIER_CNPJ) == "321"
    assert session.calls[0]["params"] == {payload.SUPPLIER_SEARCH_PARAM: SUPPLIER_CNPJ}


def test_supplier_not_registered_blocks_with_an_actionable_message():
    other = {payload.SUPPLIER_ID_KEY: "9", payload.SUPPLIER_TAX_ID_KEYS[0]: OTHER_CNPJ}
    session = FakeSession({("GET", "fornecedores"): [other]})
    with pytest.raises(ExportError) as raised:
        resolve_supplier_id(reader(session), SUPPLIER_CNPJ)
    assert raised.value.code == "supplier_not_found"
    assert raised.value.retryable is False
    assert "Cadastre o fornecedor" in raised.value.message


def test_lookup_only_reads():
    _, session = lookup([expense()])
    assert set(session.methods()) == {"GET"}


def test_finds_the_same_supplier_amount_and_due_date():
    found, _ = lookup([expense("77")])
    assert found == "77"


def test_matches_when_the_erp_has_the_date_only_in_the_expense_date_field():
    row = expense("78", due="", issued="20/07/2026")
    found, _ = lookup([row])
    assert found == "78"


def test_amount_is_the_sum_of_the_allocations():
    row = expense("79", amount="400.00")
    row["apropriacao"].append({"st_conta_cont": "2.1.03", "vl_valor_apro": "600.00"})
    found, _ = lookup([row])
    assert found == "79"


@pytest.mark.parametrize(
    "row",
    [
        expense(tax_id=OTHER_CNPJ),
        expense(amount="1000.50"),
        expense(due="21/08/2026", issued="21/08/2026"),
    ],
    ids=["outro fornecedor", "outro valor", "outro vencimento"],
)
def test_does_not_confuse_a_similar_but_different_expense(row):
    found, _ = lookup([row])
    assert found is None


def test_a_recurring_expense_of_another_month_is_not_a_duplicate():
    # Mesmo fornecedor e mesmo valor, mas de outro mês.
    found, _ = lookup([expense("80", due="20/06/2026", issued="20/06/2026")])
    assert found is None


def test_reads_further_pages_until_it_finds_the_expense():
    session = FakeSession(
        {("GET", "despesas"): pages([expense("1", amount="1.00")], [expense("2")])}
    )
    assert find_existing_expense(reader(session), draft()) == "2"
    assert len(session.calls) == 2


def test_stops_when_the_api_ignores_the_page_parameter():
    same = [expense("1", amount="1.00")]
    calls = []

    def handler(**kwargs):
        calls.append(1)
        return FakeResponse(200, same)

    session = FakeSession({("GET", "despesas"): handler})
    assert find_existing_expense(reader(session), draft()) is None
    assert len(calls) == 2  # a segunda página não trouxe id novo


def test_query_is_scoped_to_the_condominium_and_a_date_window():
    _, session = lookup([expense()])
    params = session.calls[0]["params"]
    assert params["idCondominio"] == CONDOMINIUM_ERP_ID
    assert params["dtInicio"] < "2026-07-20" < params["dtFim"]
