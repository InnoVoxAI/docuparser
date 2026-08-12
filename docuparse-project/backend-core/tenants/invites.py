"""Lógica de convite de tenant (geração de token, envio de email, ativação e
reenvio) — generalizada por papel na feature 019-generalize-tenant-invite
(originalmente exclusiva de admin, feature 017-tenant-admin-onboarding).

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

from tenants.models import Invite, Tenant, UserProfile

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

logger = logging.getLogger(__name__)


class InviteNotFoundError(Exception):
    """Raised when no invite matches the given token."""


class InviteExpiredError(Exception):
    """Raised when the invite exists but is expired or invalidated (superseded)."""


class InviteAlreadyUsedError(Exception):
    """Raised when the invite has already been consumed."""


class InviteeAlreadyActiveError(Exception):
    """Raised when a resend is requested but the invitee already has a usable password."""


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def send_invite_email(
    invite: Invite, email: str, raw_token: str, role_display_name: str
) -> None:
    context = {
        "invitee_name": invite.user.first_name,
        "tenant_name": invite.tenant.name,
        "role_display_name": role_display_name,
        "activation_link": f"{settings.FRONTEND_BASE_URL}/ativar-conta/{raw_token}",
        "expires_at": invite.expires_at,
    }
    subject = render_to_string("tenants/emails/invite_subject.txt", context).strip()
    body = render_to_string("tenants/emails/invite_body.txt", context)

    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email])
    except Exception:
        logger.exception("Failed to send invite email for invite %s", invite.id)
        raise

    logger.info("Invite email sent for invite %s", invite.id)


def _issue_invite(
    user: AbstractBaseUser, tenant: Tenant, email: str, role_display_name: str
) -> Invite:
    raw_token = generate_invite_token()
    invite = Invite.objects.create(
        user=user,
        tenant=tenant,
        token_hash=hash_token(raw_token),
        expires_at=timezone.now()
        + timezone.timedelta(hours=settings.TENANT_ADMIN_INVITE_TTL_HOURS),
    )
    send_invite_email(invite, email, raw_token, role_display_name)
    return invite


def create_invite(tenant: Tenant, name: str, email: str, role: Role) -> Invite:
    """Create a user with no usable password, assign them to ``tenant`` with
    ``role``, and email an activation link.
    """
    User = get_user_model()
    user = User(username=email, email=email, first_name=name, is_active=True)
    user.set_unusable_password()
    user.save()

    UserProfile.objects.create(user=user, tenant=tenant, role_ref=role)

    return _issue_invite(user, tenant, email, role.name if role else "")


def create_admin_invite(tenant: Tenant, admin_name: str, admin_email: str) -> Invite:
    admin_role = Role.objects.filter(name="admin").first()
    return create_invite(tenant, admin_name, admin_email, admin_role)


def resend_invite(tenant: Tenant, user_id: int) -> Invite:
    """Invalidate the invitee's pending invite (if any) and issue a new one.

    Raises ``InviteeAlreadyActiveError`` if the invitee has already set a usable
    password — resending would be pointless and could confuse an active user.
    """
    profile = UserProfile.objects.select_related("user", "role_ref").get(
        tenant=tenant, user_id=user_id
    )
    user = profile.user
    if user.has_usable_password():
        raise InviteeAlreadyActiveError()

    Invite.objects.filter(user=user, status=Invite.Status.PENDING).update(
        status=Invite.Status.INVALIDATED
    )

    role_display_name = profile.role_ref.name if profile.role_ref else ""
    return _issue_invite(user, tenant, user.email, role_display_name)


def resend_admin_invite(tenant: Tenant) -> Invite:
    """Thin wrapper over ``resend_invite`` preserving the existing admin-resend
    contract (``POST /api/admin/tenants/{slug}/invites/resend/``, no body).
    """
    profile = UserProfile.objects.get(tenant=tenant, role_ref__name="admin")
    return resend_invite(tenant, profile.user_id)


def activate_invite(token: str, password: str) -> AbstractBaseUser:
    """Validate an invite token and set the invited user's password.

    Raises ``InviteNotFoundError``/``InviteExpiredError``/``InviteAlreadyUsedError``
    for an invalid token, or ``django.core.exceptions.ValidationError`` if the
    password fails ``AUTH_PASSWORD_VALIDATORS`` — in both cases the invite is left
    untouched (not marked as used).
    """
    try:
        invite = Invite.objects.select_related("user", "tenant").get(
            token_hash=hash_token(token)
        )
    except Invite.DoesNotExist:
        raise InviteNotFoundError() from None

    if invite.status == Invite.Status.USED:
        raise InviteAlreadyUsedError()
    if (
        invite.status == Invite.Status.INVALIDATED
        or invite.expires_at <= timezone.now()
    ):
        raise InviteExpiredError()

    validate_password(password, user=invite.user)

    invite.user.set_password(password)
    invite.user.save(update_fields=["password"])

    invite.status = Invite.Status.USED
    invite.used_at = timezone.now()
    invite.save(update_fields=["status", "used_at", "updated_at"])

    return invite.user
