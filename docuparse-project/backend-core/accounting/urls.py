from django.urls import path

from .views import (
    chart_of_accounts_detail_view,
    charts_of_accounts_view,
    condominium_ledger_accounts_view,
    document_condominium_view,
    document_ledger_account_view,
    ledger_account_detail_view,
    ledger_accounts_view,
    supplier_rule_detail_view,
    supplier_rules_view,
)

# Contas são aninhadas sob o plano; regras de fornecedor, sob o condomínio; a conta do documento, sob o documento.
urlpatterns = [
    path("charts-of-accounts", charts_of_accounts_view, name="charts-of-accounts"),
    path(
        "charts-of-accounts/<uuid:chart_id>",
        chart_of_accounts_detail_view,
        name="chart-of-accounts-detail",
    ),
    path(
        "charts-of-accounts/<uuid:chart_id>/ledger-accounts",
        ledger_accounts_view,
        name="ledger-accounts",
    ),
    path(
        "charts-of-accounts/<uuid:chart_id>/ledger-accounts/<uuid:ledger_account_id>",
        ledger_account_detail_view,
        name="ledger-account-detail",
    ),
    # Leitura das contas do plano do condomínio (usada pelo painel de revisão).
    path(
        "condominiums/<uuid:condominium_id>/ledger-accounts",
        condominium_ledger_accounts_view,
        name="condominium-ledger-accounts",
    ),
    path(
        "condominiums/<uuid:condominium_id>/supplier-rules",
        supplier_rules_view,
        name="supplier-rules",
    ),
    path(
        "condominiums/<uuid:condominium_id>/supplier-rules/<uuid:supplier_rule_id>",
        supplier_rule_detail_view,
        name="supplier-rule-detail",
    ),
    path(
        "documents/<uuid:document_id>/ledger-account",
        document_ledger_account_view,
        name="document-ledger-account",
    ),
    path(
        "documents/<uuid:document_id>/condominium",
        document_condominium_view,
        name="document-condominium",
    ),
]
