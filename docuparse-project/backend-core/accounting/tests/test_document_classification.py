"""Persistência da classificação: estado atual, DocumentEvent e histórico."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from condominiums.models import Condominium
from condominiums.tests.base import TenantAPITestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from documents.models import Document, DocumentEvent, ExtractionResult
from events import validate_event

from accounting.models import DocumentClassification, LedgerAccount, SupplierRule
from accounting.services import (
    NO_RULE_REASON,
    classify_document,
    facts_for_document,
    set_manual_classification,
)

COMPESA_CNPJ = "09769035000164"


class DocumentClassificationTests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.condominium = Condominium.objects.create(name="Edifício Exemplo")
        self.water = self._account("2.1.01", "Água")
        self.maintenance = self._account("2.3.01", "Manutenções")
        self.rule = SupplierRule.objects.create(
            condominium=self.condominium,
            supplier_tax_id=COMPESA_CNPJ,
            ledger_account=self.water,
        )
        self.document = Document.objects.create(
            channel="manual",
            file_uri="local://documents/condos/doc/original",
            original_filename="fatura.pdf",
        )
        ExtractionResult.objects.create(
            document=self.document,
            schema_id="conta_de_agua",
            schema_version="v1",
            fields={"cnpj_emissor": {"value": "09.769.035/0001-64", "confidence": 0.9}},
        )
        self.user = get_user_model().objects.get(username="reviewer@condos.test")

    def _account(self, code: str, name: str) -> LedgerAccount:
        return LedgerAccount.objects.create(
            condominium=self.condominium, code=code, name=name
        )

    def _events(self) -> list[DocumentEvent]:
        return list(
            self.document.events.filter(event_type="document.classified").order_by(
                "occurred_at"
            )
        )

    # ── classificação automática ─────────────────────────────────────────────
    def test_automatic_classification_stores_state_and_event(self) -> None:
        classification = classify_document(self.document, self.condominium)

        assert classification.ledger_account == self.water
        assert classification.origin == "automatic"
        assert classification.rule_id == "supplier"
        (event,) = self._events()
        data = event.payload["data"]
        assert data["applied"] is True
        assert data["ledger_account"]["code"] == "2.1.01"
        assert data["previous_ledger_account"] is None
        assert event.correlation_id == self.document.correlation_id

    def test_event_payload_follows_the_contract(self) -> None:
        classify_document(self.document, self.condominium)
        (event,) = self._events()
        parsed = validate_event(event.payload)
        assert parsed.event_type == "document.classified"
        assert parsed.tenant_id == self.tenant.slug

    def test_no_matching_rule_records_event_without_state(self) -> None:
        self.rule.delete()
        assert classify_document(self.document, self.condominium) is None
        assert not DocumentClassification.objects.filter(
            document=self.document
        ).exists()
        (event,) = self._events()
        assert event.payload["data"]["applied"] is False
        assert event.payload["data"]["ledger_account"] is None
        assert event.payload["data"]["reason"] == NO_RULE_REASON

    def test_reclassifying_keeps_one_state_and_every_event(self) -> None:
        classify_document(self.document, self.condominium)
        self.rule.ledger_account = self.maintenance
        self.rule.save()
        classification = classify_document(self.document, self.condominium)

        assert (
            DocumentClassification.objects.filter(document=self.document).count() == 1
        )
        assert classification.ledger_account == self.maintenance
        first, second = self._events()
        assert second.payload["data"]["previous_ledger_account"]["id"] == str(
            self.water.id
        )
        assert first.payload["data"]["ledger_account"]["id"] == str(self.water.id)

    # ── classificação manual ─────────────────────────────────────────────────
    def test_manual_classification_records_who_and_from_to(self) -> None:
        classify_document(self.document, self.condominium)
        classification = set_manual_classification(
            self.document, self.maintenance, self.user
        )

        assert classification.origin == "manual"
        assert classification.classified_by == self.user
        manual = self._events()[-1].payload["data"]
        assert manual["origin"] == "manual"
        assert manual["classified_by"] == self.user.get_username()
        assert manual["previous_ledger_account"]["code"] == "2.1.01"
        assert manual["ledger_account"]["code"] == "2.3.01"

    def test_automatic_run_never_replaces_a_manual_choice(self) -> None:
        set_manual_classification(self.document, self.maintenance, self.user)
        classification = classify_document(self.document, self.condominium)

        assert classification.ledger_account == self.maintenance
        assert classification.origin == "manual"
        suggestion = self._events()[-1].payload["data"]
        assert suggestion["applied"] is False
        assert suggestion["ledger_account"]["code"] == "2.1.01"
        assert suggestion["previous_ledger_account"]["code"] == "2.3.01"

    def test_history_is_preserved_across_reclassifications(self) -> None:
        classify_document(self.document, self.condominium)
        set_manual_classification(self.document, self.maintenance, self.user)
        set_manual_classification(self.document, self.water, self.user)

        steps = [
            (
                e.payload["data"]["previous_ledger_account"],
                e.payload["data"]["ledger_account"],
            )
            for e in self._events()
        ]
        codes = [(prev and prev["code"], new and new["code"]) for prev, new in steps]
        assert codes == [(None, "2.1.01"), ("2.1.01", "2.3.01"), ("2.3.01", "2.1.01")]

    def test_history_survives_renaming_the_account(self) -> None:
        classify_document(self.document, self.condominium)
        self.water.name = "Água e esgoto"
        self.water.save()
        (event,) = self._events()
        assert event.payload["data"]["ledger_account"]["name"] == "Água"

    def test_account_in_use_cannot_be_deleted(self) -> None:
        from django.db.models import ProtectedError

        classify_document(self.document, self.condominium)
        self.rule.delete()
        with self.assertRaises(ProtectedError):
            self.water.delete()

    # ── fatos do documento ───────────────────────────────────────────────────
    def test_facts_flatten_extracted_fields_and_read_raw_text(self) -> None:
        self.document.raw_text_uri = "local://raw.json"
        storage = MagicMock()
        storage.get_bytes.return_value = json.dumps({"raw_text": "FATURA"}).encode()
        with patch("accounting.services.get_storage", return_value=storage):
            facts = facts_for_document(self.document)
        assert facts.fields == {"cnpj_emissor": "09.769.035/0001-64"}
        assert facts.raw_text == "FATURA"

    def test_facts_without_raw_text_uri_do_not_touch_storage(self) -> None:
        with patch("accounting.services.get_storage") as get_storage:
            assert facts_for_document(self.document).raw_text == ""
        get_storage.assert_not_called()


class ManualClassificationAPITests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.authenticate("reviewer")
        self.condominium = Condominium.objects.create(name="Edifício Exemplo")
        self.water = LedgerAccount.objects.create(
            condominium=self.condominium, code="2.1.01", name="Água"
        )
        self.document = Document.objects.create(
            channel="manual",
            file_uri="local://documents/condos/doc/original",
            condominium=self.condominium,
        )
        self.url = reverse("document-ledger-account", args=[self.document.id])

    def _put(self, account_id: object):
        return self.client.put(
            self.url, {"ledger_account_id": str(account_id)}, format="json"
        )

    def test_reviewer_sets_the_account_and_an_event_is_recorded(self) -> None:
        response = self._put(self.water.id)
        assert response.status_code == 200
        body = response.json()
        assert body["ledger_account_id"] == str(self.water.id)
        assert body["origin"] == "manual"
        assert body["classified_by"] == "reviewer@condos.test"
        event = self.document.events.get(event_type="document.classified")
        assert event.payload["data"]["classified_by"] == "reviewer@condos.test"

    def test_changing_the_account_keeps_both_events(self) -> None:
        other = LedgerAccount.objects.create(
            condominium=self.condominium, code="2.3.01", name="Manutenções"
        )
        self._put(self.water.id)
        self._put(other.id)
        assert (
            self.document.events.filter(event_type="document.classified").count() == 2
        )
        assert (
            DocumentClassification.objects.get(document=self.document).ledger_account
            == other
        )

    def test_requires_documents_validate_permission(self) -> None:
        self.authenticate("operator")
        assert self._put(self.water.id).status_code == 403
        assert not self.document.events.exists()

    def test_rejects_inactive_or_unknown_account(self) -> None:
        self.water.is_active = False
        self.water.save()
        inactive = self._put(self.water.id)
        assert inactive.status_code == 400
        assert "ledger_account_id" in inactive.json()
        unknown = self._put("00000000-0000-4000-8000-000000000000")
        assert unknown.status_code == 400

    def test_unknown_document_is_404(self) -> None:
        url = reverse(
            "document-ledger-account", args=["00000000-0000-4000-8000-000000000000"]
        )
        assert (
            self.client.put(
                url, {"ledger_account_id": str(self.water.id)}, format="json"
            ).status_code
            == 404
        )

    def test_service_token_is_refused_because_there_is_no_user_to_credit(self) -> None:
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer secret", HTTP_X_TENANT=self.tenant.slug
        )
        with self.settings(DOCUPARSE_INTERNAL_SERVICE_TOKEN="secret"):
            response = self._put(self.water.id)
        assert response.status_code == 403
        assert not self.document.events.exists()

    def test_requires_the_documents_condominium_first(self) -> None:
        self.document.condominium = None
        self.document.save()
        response = self._put(self.water.id)
        assert response.status_code == 400
        assert "condomínio" in response.json()["ledger_account_id"][0]
        assert not self.document.events.exists()

    def test_account_must_belong_to_the_documents_condominium(self) -> None:
        other = Condominium.objects.create(name="Outro Edifício")
        foreign = LedgerAccount.objects.create(
            condominium=other, code="2.1.01", name="Água"
        )
        response = self._put(foreign.id)
        assert response.status_code == 400
        assert "ledger_account_id" in response.json()
