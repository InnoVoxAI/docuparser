from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

DEFAULT_EMAIL = "admin@docuparse.com"
DEFAULT_PASSWORD = "admin123"
DEFAULT_USERNAME = "admin"


class Command(BaseCommand):
    help = "Seed default admin superuser (idempotent)"

    def handle(self, *args: object, **options: object) -> None:
        email = os.environ.get("DOCUPARSE_ADMIN_EMAIL", DEFAULT_EMAIL)
        password = os.environ.get("DOCUPARSE_ADMIN_PASSWORD", DEFAULT_PASSWORD)
        username = os.environ.get("DOCUPARSE_ADMIN_USERNAME", DEFAULT_USERNAME)

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f"seed_admin: user '{email}' already exists, skipping."))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"seed_admin: superuser '{email}' created."))
