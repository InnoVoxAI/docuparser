"""A classificação em conta roda nos pontos do pipeline que gravam a extração."""

from __future__ import annotations

import json
from contextlib import ExitStack
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from accounting.models import DocumentClassification, LedgerAccount, SupplierRule
from catalog.models import SchemaConfig
from condominiums.models import Condominium
from condominiums.tests.base import TenantAPITestCase

from documents.models import Document, ExtractionResult
from documents.services.event_consumers import consume_extraction_completed
from documents.services.ocr_processor import (
    auto_extract_after_ocr,
    run_langextract_for_document,
)

EXAMPLE_CNPJ = "11222333000181"
COMPESA = "09769035000164"
BOLETO_FIELDS = {
    "cnpj_cpf_pagador": "11.222.333/0001-81",
    "cnpj_cpf_beneficiario": "09.769.035/0001-64",
}
RECEIPT_TEXT = """RECIBO
Recebi do condomínio Exemplo, CNPJ 11.222.333/0001-81, a importância de
R$ 500,00 referente a serviços prestados como gerente administrativo.
Fulano de Tal
CPF: 529.982.247-25"""


class PipelineClassificationTests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.condominium = Condominium.objects.create(
            name="Edifício Exemplo", cnpj=EXAMPLE_CNPJ
        )
        self.water = LedgerAccount.objects.create(
            condominium=self.condominium, code="2.1.01", name="Água"
        )
        self.individual_services = LedgerAccount.objects.create(
            condominium=self.condominium,
            code="2.5.01",
            name="Prestação Serviço P-física",
            nature=LedgerAccount.Nature.SERVICO_PESSOA_FISICA,
        )
        SupplierRule.objects.create(
            condominium=self.condominium,
            supplier_tax_id=COMPESA,
            ledger_account=self.water,
        )
        self.document = Document.objects.create(
            channel="manual",
            file_uri="local://documents/condos/doc/original",
            raw_text_uri="local://documents/condos/doc/ocr/raw_text.json",
        )
        self.schema = SchemaConfig.objects.create(
            schema_id="pipeline_schema", version="v1", definition={"fields": []}
        )

    def _storage(self, raw_text: str) -> ExitStack:
        storage = MagicMock()
        storage.get_bytes.return_value = json.dumps({"raw_text": raw_text}).encode()
        stack = ExitStack()
        for target in (
            "documents.services.ocr_processor.get_storage",
            "accounting.services.get_storage",
        ):
            stack.enter_context(patch(target, return_value=storage))
        return stack

    def _langextract(self, fields: dict) -> patch:
        client = patch("documents.services.ocr_processor.LangExtractClient")
        started = client.start()
        started.return_value.extract_with_schema.return_value = {
            "fields": fields,
            "confidence": 0.9,
        }
        self.addCleanup(client.stop)
        return started

    def _classification(self) -> DocumentClassification | None:
        # `.filter().first()` em vez de `.get()`: uma falha de teste com DoesNotExist
        # faz o pytest exibir o QuerySet (que consulta o banco) e abortar a transação.
        return DocumentClassification.objects.filter(document=self.document).first()

    def _event_types(self) -> list[str]:
        return list(
            self.document.events.order_by("occurred_at").values_list(
                "event_type", flat=True
            )
        )

    def _assert_classified_as_water(self) -> None:
        self.document.refresh_from_db()
        assert self.document.condominium == self.condominium
        classification = self._classification()
        assert classification is not None
        assert classification.ledger_account == self.water
        assert self._event_types() == [
            "document.condominium_identified",
            "document.classified",
        ]

    # ── os pontos que gravam a extração ──────────────────────────────────────
    def test_automatic_extraction_after_ocr_classifies_the_document(self) -> None:
        self._langextract(BOLETO_FIELDS)
        with (
            self._storage("texto do boleto"),
            patch(
                "documents.services.ocr_processor._resolve_schema_for_extraction",
                return_value=self.schema,
            ),
        ):
            auto_extract_after_ocr(self.document)
        self._assert_classified_as_water()

    def test_manual_extraction_classifies_the_document(self) -> None:
        self._langextract(BOLETO_FIELDS)
        with self._storage("texto do boleto"):
            run_langextract_for_document(self.document.id, self.schema.id)
        self._assert_classified_as_water()

    def test_extraction_completed_event_classifies_the_document(self) -> None:
        payload = {
            "event_id": str(uuid4()),
            "event_type": "extraction.completed",
            "event_version": "v1",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "tenant_id": self.tenant.slug,
            "document_id": str(self.document.id),
            "correlation_id": str(self.document.correlation_id),
            "source": "langextract-service",
            "data": {
                "schema_id": "boleto",
                "schema_version": "v1",
                "fields": BOLETO_FIELDS,
                "confidence": 0.9,
                "requires_human_validation": True,
                "metadata": {},
            },
        }
        self.document.raw_text_uri = ""
        self.document.save()
        consume_extraction_completed(payload)

        self.document.refresh_from_db()
        assert self.document.condominium == self.condominium
        classification = self._classification()
        assert classification is not None
        assert classification.ledger_account == self.water
        assert "document.classified" in self._event_types()

    def test_document_without_schema_is_still_classified_from_the_raw_text(
        self,
    ) -> None:
        with (
            self._storage(RECEIPT_TEXT),
            patch(
                "documents.services.ocr_processor._resolve_schema_for_extraction",
                return_value=None,
            ),
        ):
            auto_extract_after_ocr(self.document)

        assert not ExtractionResult.objects.filter(document=self.document).exists()
        classification = self._classification()
        assert classification is not None
        assert classification.ledger_account == self.individual_services
        assert classification.rule_id == "recibo_pessoa_fisica"
        self.document.refresh_from_db()
        assert self.document.condominium == self.condominium

    # ── isolamento de falhas e tenants sem o recurso ─────────────────────────
    def test_classification_failure_does_not_break_the_extraction(self) -> None:
        self._langextract(BOLETO_FIELDS)
        with (
            self._storage("texto do boleto"),
            patch(
                "documents.services.ocr_processor._resolve_schema_for_extraction",
                return_value=self.schema,
            ),
            patch(
                "accounting.services.identify_condominium",
                side_effect=RuntimeError("boom"),
            ),
        ):
            auto_extract_after_ocr(self.document)

        self.document.refresh_from_db()
        assert self.document.status == Document.Status.VALIDATION_PENDING
        assert ExtractionResult.objects.filter(document=self.document).exists()
        assert not DocumentClassification.objects.exists()

    def test_extraction_failure_still_propagates(self) -> None:
        client = self._langextract(BOLETO_FIELDS)
        client.return_value.extract_with_schema.side_effect = RuntimeError("llm down")
        with (
            self._storage("texto do boleto"),
            patch(
                "documents.services.ocr_processor._resolve_schema_for_extraction",
                return_value=self.schema,
            ),
        ):
            try:
                auto_extract_after_ocr(self.document)
            except RuntimeError:
                pass
            else:
                raise AssertionError("a falha da extração deixou de propagar")
        assert not self._event_types()

    def test_tenant_without_condominiums_is_unaffected(self) -> None:
        DocumentClassification.objects.all().delete()
        SupplierRule.objects.all().delete()
        LedgerAccount.objects.all().delete()
        Condominium.objects.all().delete()
        self._langextract(BOLETO_FIELDS)
        with (
            self._storage("texto do boleto"),
            patch(
                "documents.services.ocr_processor._resolve_schema_for_extraction",
                return_value=self.schema,
            ),
        ):
            auto_extract_after_ocr(self.document)

        self.document.refresh_from_db()
        assert self.document.status == Document.Status.VALIDATION_PENDING
        assert self.document.condominium is None
        assert not self._event_types()
