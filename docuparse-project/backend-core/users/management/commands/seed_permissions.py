from __future__ import annotations

from django.core.management.base import BaseCommand

from users.models import Permission

PERMISSIONS: list[tuple[str, str]] = [
    ("inbox.view", "Visualizar Inbox"),
    ("documents.send", "Enviar Documentos"),
    ("documents.validate", "Validar Documentos"),
    ("models.create", "Criar Modelos"),
    ("models.edit", "Editar Modelos"),
    ("operations.access", "Acessar Operações"),
    ("users.manage", "Gerenciar Usuários"),
    ("roles.manage", "Gerenciar Roles"),
]


class Command(BaseCommand):
    help = "Seed predefined permissions (idempotent)"

    def handle(self, *args: object, **options: object) -> None:
        created_count = 0
        for code, description in PERMISSIONS:
            _, created = Permission.objects.get_or_create(
                code=code,
                defaults={"description": description},
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_permissions: {created_count} created, "
                f"{len(PERMISSIONS) - created_count} already existed."
            )
        )
