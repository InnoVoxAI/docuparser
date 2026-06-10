from __future__ import annotations

import os

from django.core.management.base import BaseCommand

from users.models import Permission, Role
from users.management.commands.seed_permissions import PERMISSIONS


class Command(BaseCommand):
    help = "Seed default tenant, permissions, admin role, and admin user (idempotent)"

    def handle(self, *args: object, **options: object) -> None:
        from documents.models import Tenant, UserProfile
        from django.contrib.auth import get_user_model

        User = get_user_model()

        tenant, created = Tenant.objects.get_or_create(name="default")
        if created:
            self.stdout.write("seed_data: created default tenant")

        for code, description in PERMISSIONS:
            Permission.objects.get_or_create(code=code, defaults={"description": description})
        self.stdout.write("seed_data: permissions ready")

        role, _ = Role.objects.get_or_create(name="admin")
        role.permissions.set(Permission.objects.all())
        role.save()
        self.stdout.write("seed_data: admin role ready")

        admin_email = os.environ.get("ADMIN_EMAIL", "admin@docuparse.com")
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")

        user, created = User.objects.get_or_create(
            username=admin_email,
            defaults={"email": admin_email, "is_active": True, "is_staff": True},
        )
        if created:
            user.set_password(admin_password)
            user.save()
            self.stdout.write(f"seed_data: created admin user {admin_email}")
        else:
            self.stdout.write(f"seed_data: admin user {admin_email} already exists")

        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"tenant": tenant})
        profile.role_ref = role
        profile.tenant = tenant
        profile.save()
        self.stdout.write("seed_data: admin profile ready")
