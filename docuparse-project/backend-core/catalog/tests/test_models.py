from __future__ import annotations

from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from catalog.models import LayoutConfig, SchemaConfig

# NOTA: o catálogo canônico (2 SchemaConfig + 3 LayoutConfig) já existe no banco
# de teste — `catalog/0002_seed_default_catalog` roda no setup. Os testes abaixo
# usam identificadores próprios para não colidir com o seed.


class SchemaConfigConstraintTests(TestCase):
    def test_schema_config_version_is_globally_unique(self) -> None:
        SchemaConfig.objects.create(schema_id="nf_test", version="v1", definition={})
        with self.assertRaises(IntegrityError):
            SchemaConfig.objects.create(
                schema_id="nf_test", version="v1", definition={}
            )

    def test_layout_config_is_globally_unique(self) -> None:
        schema = SchemaConfig.objects.create(
            schema_id="nf_test", version="v1", definition={}
        )
        LayoutConfig.objects.create(
            layout="layout_test", document_type="", schema_config=schema
        )
        with self.assertRaises(IntegrityError):
            LayoutConfig.objects.create(
                layout="layout_test", document_type="", schema_config=schema
            )

    def test_deleting_schema_with_layout_is_protected(self) -> None:
        schema = SchemaConfig.objects.create(
            schema_id="nf_test", version="v1", definition={}
        )
        LayoutConfig.objects.create(
            layout="layout_test", document_type="", schema_config=schema
        )
        with self.assertRaises(ProtectedError):
            schema.delete()

    def test_default_catalog_is_seeded(self) -> None:
        assert SchemaConfig.objects.filter(schema_id="nota_fiscal_default").exists()
        assert LayoutConfig.objects.filter(layout="fatura_energia").exists()
