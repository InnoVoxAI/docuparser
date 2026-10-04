from __future__ import annotations

from users.permissions import require_permission_by_method

# Vale também para o plano de contas (/condominiums/<id>/ledger-accounts).
CondominiumPermission = require_permission_by_method(
    read="inbox.view", write="models.edit"
)
