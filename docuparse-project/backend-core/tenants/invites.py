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
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from users.models import Role

from tenants.models import Tenant, TenantAdminInvite, UserProfile

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


def create_admin_invite(
    tenant: Tenant, admin_name: str, admin_email: str
) -> TenantAdminInvite:
    User = get_user_model()
    user = User(
        username=admin_email,
        email=admin_email,
        first_name=admin_name,
        is_active=True,
    )
    user.set_unusable_password()
    user.save()

    admin_role = Role.objects.filter(name="admin").first()
    UserProfile.objects.create(user=user, tenant=tenant, role_ref=admin_role)

    raw_token = generate_invite_token()
    invite = TenantAdminInvite.objects.create(
        user=user,
        tenant=tenant,
        token_hash=hash_token(raw_token),
        expires_at=timezone.now()
        + timezone.timedelta(hours=settings.TENANT_ADMIN_INVITE_TTL_HOURS),
    )
    send_admin_invite_email(invite, admin_email, raw_token)
    return invite
