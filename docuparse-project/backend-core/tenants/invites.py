"""Lógica de convite de administrador de tenant (geração de token, envio de email,
ativação e reenvio) — feature 017-tenant-admin-onboarding.

Isolado de ``tenants/views.py`` para manter esse arquivo dentro do limite de 400
linhas por arquivo exigido pela constituição do projeto.
"""

from __future__ import annotations

import hashlib
import logging
import secrets

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from tenants.models import TenantAdminInvite

logger = logging.getLogger(__name__)


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def send_admin_invite_email(
    invite: TenantAdminInvite, admin_email: str, raw_token: str
) -> None:
    context = {
        "admin_name": invite.user.first_name,
        "tenant_name": invite.tenant.name,
        "activation_link": f"{settings.FRONTEND_BASE_URL}/ativar-conta/{raw_token}",
        "expires_at": invite.expires_at,
    }
    subject = render_to_string(
        "tenants/emails/admin_invite_subject.txt", context
    ).strip()
    body = render_to_string("tenants/emails/admin_invite_body.txt", context)

    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [admin_email])
    except Exception:
        logger.exception(
            "Failed to send tenant admin invite email for invite %s", invite.id
        )
        raise

    logger.info("Tenant admin invite email sent for invite %s", invite.id)
