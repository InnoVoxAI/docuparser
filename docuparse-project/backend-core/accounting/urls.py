from django.urls import path

from .views import ledger_account_detail_view, ledger_accounts_view

# Aninhado sob o condomínio: o plano de contas é por condomínio.
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
]
