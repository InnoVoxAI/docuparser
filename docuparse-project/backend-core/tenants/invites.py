"""Lógica de convite de administrador de tenant (geração de token, envio de email,
ativação e reenvio) — feature 017-tenant-admin-onboarding.

Isolado de ``tenants/views.py`` para manter esse arquivo dentro do limite de 400
linhas por arquivo exigido pela constituição do projeto.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from users.models import Role

from tenants.models import Tenant, TenantAdminInvite, UserProfile

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

logger = logging.getLogger(__name__)


class InviteNotFoundError(Exception):
    """Raised when no invite matches the given token."""


class InviteExpiredError(Exception):
    """Raised when the invite exists but is expired or invalidated (superseded)."""


class InviteAlreadyUsedError(Exception):
    """Raised when the invite has already been consumed."""


class AdminAlreadyActiveError(Exception):
    """Raised when a resend is requested but the tenant admin already has a usable password."""


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


def _issue_invite(
    user: AbstractBaseUser, tenant: Tenant, admin_email: str
) -> TenantAdminInvite:
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

    return _issue_invite(user, tenant, admin_email)


def resend_admin_invite(tenant: Tenant) -> TenantAdminInvite:
    """Invalidate the tenant admin's pending invite (if any) and issue a new one.

    Raises ``AdminAlreadyActiveError`` if the admin has already set a usable
    password — resending would be pointless and could confuse an active admin.
    """
    profile = UserProfile.objects.select_related("user").get(
        tenant=tenant, role_ref__name="admin"
    )
    user = profile.user
    if user.has_usable_password():
        raise AdminAlreadyActiveError()

    TenantAdminInvite.objects.filter(
        user=user, status=TenantAdminInvite.Status.PENDING
    ).update(status=TenantAdminInvite.Status.INVALIDATED)

    return _issue_invite(user, tenant, user.email)


def activate_invite(token: str, password: str) -> AbstractBaseUser:
    """Validate an invite token and set the invited user's password.

    Raises ``InviteNotFoundError``/``InviteExpiredError``/``InviteAlreadyUsedError``
    for an invalid token, or ``django.core.exceptions.ValidationError`` if the
    password fails ``AUTH_PASSWORD_VALIDATORS`` — in both cases the invite is left
    untouched (not marked as used).
    """
    try:
        invite = TenantAdminInvite.objects.select_related("user", "tenant").get(
            token_hash=hash_token(token)
        )
    except TenantAdminInvite.DoesNotExist:
        raise InviteNotFoundError() from None

    if invite.status == TenantAdminInvite.Status.USED:
        raise InviteAlreadyUsedError()
    if (
        invite.status == TenantAdminInvite.Status.INVALIDATED
        or invite.expires_at <= timezone.now()
    ):
        raise InviteExpiredError()

    validate_password(password, user=invite.user)

    invite.user.set_password(password)
    invite.user.save(update_fields=["password"])

    invite.status = TenantAdminInvite.Status.USED
    invite.used_at = timezone.now()
    invite.save(update_fields=["status", "used_at", "updated_at"])

    return invite.user
