from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Tenant(TenantMixin, TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    auto_create_schema = True

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.slug

    def save(self, *args: object, **kwargs: object) -> None:
        # Same tenant_<slug> convention used by the provisioning API and by
        # migration 0002's backfill — default it here so every creation path
        # (including ad-hoc ones, e.g. in tests) doesn't have to repeat it.
        if not self.schema_name:
            self.schema_name = f"tenant_{self.slug}"
        super().save(*args, **kwargs)


class Domain(DomainMixin):
    pass


class UserProfile(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="docuparse_profile",
    )
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="profiles"
    )
    role_ref = models.ForeignKey(
        "users.Role",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="user_profiles",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user"],
                name="unique_tenant_profile_per_tenant_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}@{self.tenant_id}"


class TenantAdminInvite(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        USED = "USED", "Used"
        INVALIDATED = "INVALIDATED", "Invalidated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_invites",
    )
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="admin_invites"
    )
    token_hash = models.CharField(max_length=128, unique=True, db_index=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user_id}@{self.tenant_id} ({self.status})"
