"""Lógica de convite de administrador de tenant (geração de token, envio de email,
ativação e reenvio) — feature 017-tenant-admin-onboarding.

Isolado de ``tenants/views.py`` para manter esse arquivo dentro do limite de 400
linhas por arquivo exigido pela constituição do projeto.
"""

from __future__ import annotations
