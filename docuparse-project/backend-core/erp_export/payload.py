"""Contrato de escrita da despesa no Superlógica.

ATENÇÃO: nada neste arquivo foi verificado contra a API de escrita. A documentação
pública (Postman) só confirma o padrão `/v2/condor/CONTROLLER/ACTION`, os headers
`app_token` e `access_token`, a data no formato `MM/DD/AAAA` e que os nomes dos
parâmetros diferenciam maiúsculas de minúsculas. O endpoint de despesas e os campos
abaixo são HIPÓTESE, derivada dos nomes que a leitura (`GET despesas`) já devolve.

Por isso `CONTRACT_VERIFIED` começa `False`. Enquanto for `False`, a política
(`policy.py`) recusa o modo `live`; só `dry-run` e `sandbox` usam este mapeamento.
Quando o spike (ticket 1) confirmar o contrato em ambiente de teste, corrija os nomes
aqui e então troque a constante.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from erp_export.draft import ExpenseDraft

CONTRACT_VERIFIED = False

# Único endpoint de escrita que o conector pode chamar (ver writer.ALLOWED_WRITES).
EXPENSE_PATH = "despesas"

# HIPÓTESE (leitura de fornecedores): caminho, parâmetro de busca e nomes das chaves.
# Nenhum destes nomes foi verificado; o spike deve confirmá-los ou corrigi-los aqui.
SUPPLIER_LIST_PATH = "fornecedores"
SUPPLIER_SEARCH_PARAM = "pesquisa"
SUPPLIER_ID_KEY = "id_fornecedor_for"
SUPPLIER_TAX_ID_KEYS = ("st_cnpj_for", "st_cpf_for", "st_cpfcnpj_for")


def _us_date(value: date) -> str:
    """O Superlógica documenta a data como MM/DD/AAAA."""
    return value.strftime("%m/%d/%Y")


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def build_expense_body(draft: ExpenseDraft, supplier_id: str) -> dict[str, Any]:
    """HIPÓTESE: corpo do POST de despesa. Não enviar em `live` antes do spike."""
    body: dict[str, Any] = {
        "ID_CONDOMINIO_COND": draft.condominium_external_id,
        "ID_FORNECEDOR_FOR": supplier_id,
        "ID_PLANOCONTA_PLC": draft.chart_external_id,
        "DT_DESPESA_DES": _us_date(draft.issue_date or draft.due_dates[0]),
        "ST_DOCUMENTO_DES": draft.document_number,
        "ST_COMPLEMENTO_DES": draft.description,
        "APROPRIACAO": [
            {
                "ST_CONTA_CONT": draft.account_code,
                "VL_VALOR_APRO": _money(draft.amount),
            }
        ],
        "PARCELAS": [
            {
                "DT_VENCIMENTO_PDES": _us_date(installment.due_date),
                "VL_VALOR_PDES": _money(installment.amount),
            }
            for installment in draft.installments
        ],
    }
    return {key: value for key, value in body.items() if value not in ("", None)}
