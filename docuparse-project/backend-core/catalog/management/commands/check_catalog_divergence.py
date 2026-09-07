"""Verificação read-only de divergência do catálogo por-tenant (spec 018, FR-010).

Roda ANTES do deploy destrutivo (com o código antigo ainda no ar): para cada
schema de tenant, lê as tabelas legadas `documents_schemaconfig` /
`documents_layoutconfig` e compara com o conjunto canônico de
`catalog.defaults.default_catalog_specs()`. Se algum tenant tiver linha fora do
canônico, lista os ofensores e sai com código 1 — o operador decide se a linha
customizada entra no catálogo global (`catalog/defaults.py`) ou é descartada.

Idempotente e sem efeitos colaterais. Após `0015_drop_catalog_models` as tabelas
legadas somem e o comando passa a não achar nada (sai limpo).
"""

from __future__ import annotations

import sys

from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import schema_context

from catalog.defaults import default_catalog_specs


class Command(BaseCommand):
    help = (
        "Lista SchemaConfig/LayoutConfig legados fora do catálogo canônico (read-only)."
    )

    def handle(self, *args: object, **options: object) -> None:
        from tenants.models import Tenant

        specs = default_catalog_specs()
        canonical_schemas = {(s["schema_id"], s["version"]) for s in specs["schemas"]}
        canonical_layouts = {
            (lc["layout"], lc["document_type"]) for lc in specs["layouts"]
        }

        offenders: list[str] = []

        for tenant in Tenant.objects.all():
            with schema_context(tenant.schema_name):
                if not self._table_exists("documents_schemaconfig"):
                    continue
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT schema_id, version FROM documents_schemaconfig"
                    )
                    for row in cursor.fetchall():
                        if tuple(row) not in canonical_schemas:
                            offenders.append(
                                f"[{tenant.schema_name}] SchemaConfig fora do canônico: "
                                f"schema_id={row[0]!r} version={row[1]!r}"
                            )
                if self._table_exists("documents_layoutconfig"):
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT layout, document_type FROM documents_layoutconfig"
                        )
                        for row in cursor.fetchall():
                            if tuple(row) not in canonical_layouts:
                                offenders.append(
                                    f"[{tenant.schema_name}] LayoutConfig fora do canônico: "
                                    f"layout={row[0]!r} document_type={row[1]!r}"
                                )

        if offenders:
            self.stderr.write(
                self.style.ERROR(
                    "Divergência de catálogo detectada — resolva antes do deploy "
                    "(ver quickstart 018):"
                )
            )
            for line in offenders:
                self.stderr.write(f"  - {line}")
            sys.exit(1)

        self.stdout.write(
            self.style.SUCCESS(
                "Nenhuma divergência: todos os tenants têm o catálogo canônico."
            )
        )

    @staticmethod
    def _table_exists(table_name: str) -> bool:
        return table_name in connection.introspection.table_names()
