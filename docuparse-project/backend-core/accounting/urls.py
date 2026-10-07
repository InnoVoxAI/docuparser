from django.urls import path

from .views import (
    document_ledger_account_view,
    ledger_account_detail_view,
    ledger_accounts_view,
    supplier_rule_detail_view,
    supplier_rules_view,
)

# Plano de contas e regras são aninhados sob o condomínio; a conta do documento, sob o documento.
urlpatterns = [
    path(
        "condominiums/<uuid:condominium_id>/ledger-accounts",
        ledger_accounts_view,
        name="ledger-accounts",
    ),
    path(
        "condominiums/<uuid:condominium_id>/ledger-accounts/<uuid:ledger_account_id>",
        ledger_account_detail_view,
        name="ledger-account-detail",
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
]
