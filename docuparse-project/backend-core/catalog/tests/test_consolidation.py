"""Consolidação/transição do catálogo (spec 018): idempotência do seed e a
guarda de divergência que aborta o passo destrutivo (FR-009, FR-010).
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.test import TestCase

from catalog.defaults import seed_default_catalog
from catalog.models import LayoutConfig, SchemaConfig

assert_only_canonical_rows = importlib.import_module(
    "documents.migrations.0015_drop_catalog_models"
).assert_only_canonical_rows


class SeedIdempotencyTests(TestCase):
    def test_seed_default_catalog_is_idempotent(self) -> None:
        # catalog/0002 já rodou — o catálogo canônico existe (2 + 3).
        assert SchemaConfig.objects.count() == 2
        assert LayoutConfig.objects.count() == 3

        seed_default_catalog()
        seed_default_catalog()

        assert SchemaConfig.objects.count() == 2
        assert LayoutConfig.objects.count() == 3


class _FakeManager:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeModel:
    def __init__(self, rows):
        self.objects = _FakeManager(rows)


class DivergenceGuardTests(TestCase):
    def _apps(self, schema_rows, layout_rows):
        models = {
            ("documents", "SchemaConfig"): _FakeModel(schema_rows),
            ("documents", "LayoutConfig"): _FakeModel(layout_rows),
        }
        return SimpleNamespace(get_model=lambda app, name: models[(app, name)])

    _EDITOR = SimpleNamespace(connection=SimpleNamespace(schema_name="tenant_x"))

    def test_guard_passes_with_only_canonical_rows(self) -> None:
        schemas = [
            SimpleNamespace(schema_id="nota_fiscal_default", version="v1"),
            SimpleNamespace(schema_id="conta_agua_default", version="v1"),
        ]
        layouts = [
            SimpleNamespace(layout="nota_fiscal", document_type=""),
            SimpleNamespace(layout="fatura_condominio", document_type=""),
            SimpleNamespace(layout="fatura_energia", document_type=""),
        ]
        assert_only_canonical_rows(self._apps(schemas, layouts), self._EDITOR)

    def test_guard_raises_naming_schema_on_custom_row(self) -> None:
        schemas = [SimpleNamespace(schema_id="cliente_x_custom", version="v1")]
        with self.assertRaises(RuntimeError) as ctx:
            assert_only_canonical_rows(self._apps(schemas, []), self._EDITOR)
        assert "tenant_x" in str(ctx.exception)
        assert "cliente_x_custom" in str(ctx.exception)


class CheckCatalogDivergenceCommandTests(TestCase):
    def test_command_exits_zero_when_no_legacy_tables(self) -> None:
        # Pós-migração 0015 as tabelas legadas não existem — o comando sai limpo.
        call_command("check_catalog_divergence")


@pytest.mark.tenant_db
class CheckCatalogDivergenceTenantTests:
    def test_command_clean_across_real_tenants(self) -> None:
        call_command("check_catalog_divergence")
