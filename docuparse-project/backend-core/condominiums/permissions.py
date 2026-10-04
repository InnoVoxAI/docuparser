from __future__ import annotations

from users.permissions import require_permission_by_method

# Vale também para as rotas aninhadas (plano de contas e regras de fornecedor).
CondominiumPermission = require_permission_by_method(
    read="inbox.view", write="models.edit"
)
