"""Revisão da classificação pelo operador: o detalhe do documento mostra a conta
sugerida, o override troca a conta e deixa de/para + autoria nos DocumentEvent."""

from __future__ import annotations

from condominiums.models import Condominium
from condominiums.tests.base import TenantAPITestCase
from django.urls import reverse
from documents.models import Document, ExtractionResult

from accounting.models import LedgerAccount, SupplierRule
from accounting.services import run_classification

EXAMPLE_CNPJ = "11222333000181"
COMPESA = "09769035000164"


class ClassificationReviewAPITests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.authenticate("reviewer")
        self.condominium = Condominium.objects.create(
            name="Edifício Exemplo", cnpj=EXAMPLE_CNPJ
        )
        self.water = LedgerAccount.objects.create(
            condominium=self.condominium, code="2.1.01", name="Água"
        )
        self.maintenance = LedgerAccount.objects.create(
            condominium=self.condominium, code="2.3.01", name="Manutenções"
        )
        SupplierRule.objects.create(
            condominium=self.condominium,
            supplier_tax_id=COMPESA,
            ledger_account=self.water,
        )
        self.document = Document.objects.create(
            channel="manual",
            file_uri="local://documents/condos/doc/original",
            status=Document.Status.VALIDATION_PENDING,
        )
        ExtractionResult.objects.create(
            document=self.document,
            schema_id="boleto",
            schema_version="v1",
            fields={
                "cnpj_cpf_pagador": EXAMPLE_CNPJ,
                "cnpj_cpf_beneficiario": "09.769.035/0001-64",
            },
        )
        self.detail_url = reverse("document-detail", args=[self.document.id])

    def _override(self, account: LedgerAccount):
        return self.client.put(
            reverse("document-ledger-account", args=[self.document.id]),
            {"ledger_account_id": str(account.id)},
            format="json",
        )

    def test_detail_without_classification_has_empty_fields(self) -> None:
        body = self.client.get(self.detail_url).json()
        assert body["condominium"] is None
        assert body["classification"] is None

    def test_detail_shows_the_suggested_account_and_why(self) -> None:
        run_classification(self.document)
        body = self.client.get(self.detail_url).json()

        assert body["condominium"] == {
            "id": str(self.condominium.id),
            "name": "Edifício Exemplo",
        }
        suggestion = body["classification"]
        assert suggestion["ledger_account"] == {
            "id": str(self.water.id),
            "code": "2.1.01",
            "name": "Água",
        }
        assert suggestion["origin"] == "automatic"
        assert suggestion["rule_id"] == "supplier"
        assert suggestion["classified_by"] is None

    def test_override_replaces_the_suggestion_and_credits_the_operator(self) -> None:
        run_classification(self.document)
        assert self._override(self.maintenance).status_code == 200

        classification = self.client.get(self.detail_url).json()["classification"]
        assert classification["ledger_account"]["code"] == "2.3.01"
        assert classification["origin"] == "manual"
        assert classification["classified_by"] == "reviewer@condos.test"

    def test_override_event_records_who_and_from_to(self) -> None:
        run_classification(self.document)
        self._override(self.maintenance)

        override = self.document.events.filter(event_type="document.classified").latest(
            "occurred_at"
        )
        data = override.payload["data"]
        assert data["origin"] == "manual"
        assert data["classified_by"] == "reviewer@condos.test"
        assert data["previous_ledger_account"]["code"] == "2.1.01"
        assert data["ledger_account"]["code"] == "2.3.01"

    def test_suggestion_and_override_both_stay_in_the_audit_trail(self) -> None:
        run_classification(self.document)
        self._override(self.maintenance)
        events = self.document.events.filter(event_type="document.classified")
        assert events.count() == 2

    def test_decided_documents_no_longer_accept_changes(self) -> None:
        run_classification(self.document)
        for decided in (
            Document.Status.APPROVED,
            Document.Status.REJECTED,
            Document.Status.ERP_SENT,
        ):
            Document.objects.filter(pk=self.document.pk).update(status=decided)
            response = self._override(self.maintenance)
            assert response.status_code == 409, decided
        assert (
            self.document.events.filter(event_type="document.classified").count() == 1
        )

    def test_decided_documents_keep_their_condominium(self) -> None:
        Document.objects.filter(pk=self.document.pk).update(
            status=Document.Status.APPROVED
        )
        other = Condominium.objects.create(name="Edifício Outro")
        response = self.client.put(
            reverse("document-condominium", args=[self.document.id]),
            {"condominium_id": str(other.id)},
            format="json",
        )
        assert response.status_code == 409
        self.document.refresh_from_db()
        assert self.document.condominium is None
