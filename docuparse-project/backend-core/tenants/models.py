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


class Domain(DomainMixin):
    pass


class UserProfile(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="docuparse_profile",
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="profiles")
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
