"""Cria a permissão `erp.send` e a dá aos papéis que já existem (admin e tenantAdmin).

O `seed_data` só roda em banco novo ("banco já inicializado, nada a fazer"), então
sozinho ele nunca levaria a permissão nova a um ambiente que já existe. O operador não a
recebe: enviar despesa a um sistema financeiro é uma permissão própria.
"""

from django.db import migrations

CODE = "erp.send"
DESCRIPTION = "Enviar Despesas ao ERP"
ROLES = ("admin", "tenantAdmin")


def add_permission(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")
    permission, _ = Permission.objects.get_or_create(
        code=CODE, defaults={"description": DESCRIPTION}
    )
    for role in Role.objects.filter(name__in=ROLES):
        role.permissions.add(permission)


def remove_permission(apps, schema_editor):
    apps.get_model("users", "Permission").objects.filter(code=CODE).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_role_is_platform_role"),
    ]

    operations = [
        migrations.RunPython(add_permission, remove_permission),
    ]
