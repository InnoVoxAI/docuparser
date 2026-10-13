"""Identificação do condomínio do documento. Os fatos seguem documentos reais da
cliente (boleto, DARF, guia do FGTS, fatura de concessionária), com dados fictícios."""

from __future__ import annotations

from condominiums.models import Condominium
from condominiums.tests.base import TenantAPITestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from documents.models import Document, ExtractionResult

from accounting.classification import DocumentFacts
from accounting.classification.identification import identify_condominium
from accounting.models import DocumentClassification, LedgerAccount, SupplierRule
from accounting.services import (
    NO_CONDOMINIUM_REASON,
    STALE_ACCOUNT_REASON,
    classify_document,
    identify_document_condominium,
    run_classification,
    set_document_condominium,
)

EXAMPLE_CNPJ = "11222333000181"
OTHER_CNPJ = "11444777000161"
COMPESA = "09769035000164"


class IdentifyCondominiumTests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.example = Condominium.objects.create(
            name="Edifício Exemplo", cnpj=EXAMPLE_CNPJ, aliases=["EDIFICIO EXEMPLOS"]
        )
        self.other = Condominium.objects.create(name="Edifício Outro", cnpj=OTHER_CNPJ)

    def _identify(self, facts: DocumentFacts):
        return identify_condominium(facts, Condominium.objects.all())

    def test_boleto_is_identified_by_the_payer_cnpj_field(self) -> None:
        facts = DocumentFacts(fields={"cnpj_cpf_pagador": "11.222.333/0001-81"})
        found = self._identify(facts)
        assert found.condominium == self.example
        assert found.method == "payer_tax_id"

    def test_nota_fiscal_is_identified_by_the_tomador_cnpj(self) -> None:
        found = self._identify(DocumentFacts(fields={"cnpj_tomador": OTHER_CNPJ}))
        assert found.condominium == self.other

    def test_darf_is_identified_by_the_cnpj_in_the_text(self) -> None:
        facts = DocumentFacts(
            raw_text="Documento de Arrecadação de Receitas Federais\n"
            "CNPJ 11.222.333/0001-81 CONDOMINIO DO EDIFICIO EXEMPLO"
        )
        found = self._identify(facts)
        assert found.condominium == self.example
        assert found.method == "text_tax_id"

    def test_fgts_guide_with_only_the_cnpj_root_is_identified_by_name(self) -> None:
        facts = DocumentFacts(
            raw_text="GFD - Guia do FGTS Digital\n"
            "CPF/CNPJ do Empregador 11.222.333 CONDOMINIO DO EDIFICIO EXEMPLO"
        )
        found = self._identify(facts)
        assert found.condominium == self.example
        assert found.method == "name"

    def test_utility_bill_without_payer_cnpj_is_identified_by_alias(self) -> None:
        facts = DocumentFacts(
            raw_text="CÓDIGO DO CLIENTE EDIFICIO EXEMPLOS CÓDIGO DA INSTALAÇÃO",
            fields={"cnpj_emissor": "09.769.035/0001-64"},
        )
        found = self._identify(facts)
        assert found.condominium == self.example
        assert "EXEMPLOS" in found.reason

    def test_alias_is_what_makes_the_plural_spelling_match(self) -> None:
        self.example.aliases = []
        self.example.save()
        facts = DocumentFacts(raw_text="EDIFICIO EXEMPLOS")
        assert self._identify(facts) is None

    def test_payer_field_wins_over_other_cnpjs_in_the_text(self) -> None:
        facts = DocumentFacts(
            fields={"cnpj_cpf_pagador": EXAMPLE_CNPJ},
            raw_text="Intermediado por CNPJ 11.444.777/0001-61",
        )
        assert self._identify(facts).condominium == self.example

    def test_two_condominium_cnpjs_in_the_text_are_ambiguous(self) -> None:
        facts = DocumentFacts(
            raw_text="11.222.333/0001-81 e 11.444.777/0001-61 EDIFICIO EXEMPLO"
        )
        assert self._identify(facts) is None

    def test_supplier_cnpj_alone_does_not_identify_anything(self) -> None:
        facts = DocumentFacts(raw_text="FATURA CNPJ: 09.769.035/0001-64")
        assert self._identify(facts) is None

    def test_longest_name_wins(self) -> None:
        Condominium.objects.create(name="Edifício Exemplo II")
        facts = DocumentFacts(raw_text="CONDOMINIO DO EDIFICIO EXEMPLO II")
        assert self._identify(facts).condominium.name == "Edifício Exemplo II"

    def test_names_that_match_equally_are_ambiguous(self) -> None:
        Condominium.objects.create(name="Edifício Alfa")
        Condominium.objects.create(name="Edifício Beta")
        facts = DocumentFacts(raw_text="EDIFICIO ALFA E EDIFICIO BETA")
        assert self._identify(facts) is None

    def test_inactive_condominium_is_not_identified(self) -> None:
        self.example.is_active = False
        self.example.save()
        facts = DocumentFacts(fields={"cnpj_cpf_pagador": EXAMPLE_CNPJ})
        assert self._identify(facts) is None


class DocumentCondominiumServiceTests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.example = Condominium.objects.create(
            name="Edifício Exemplo", cnpj=EXAMPLE_CNPJ
        )
        self.other = Condominium.objects.create(name="Edifício Outro", cnpj=OTHER_CNPJ)
        self.document = Document.objects.create(
            channel="manual", file_uri="local://documents/condos/doc/original"
        )
        self.user = get_user_model().objects.get(username="reviewer@condos.test")

    def _events(self, event_type: str = "document.condominium_identified"):
        return list(self.document.events.filter(event_type=event_type))

    def test_identification_fills_the_blank_and_records_an_event(self) -> None:
        facts = DocumentFacts(fields={"cnpj_cpf_pagador": EXAMPLE_CNPJ})
        assert identify_document_condominium(self.document, facts) == self.example

        self.document.refresh_from_db()
        assert self.document.condominium == self.example
        (event,) = self._events()
        data = event.payload["data"]
        assert data["applied"] is True
        assert data["method"] == "payer_tax_id"
        assert data["condominium"]["cnpj"] == EXAMPLE_CNPJ

    def test_automatic_identification_never_overwrites_an_existing_condominium(
        self,
    ) -> None:
        set_document_condominium(self.document, self.other, self.user)
        facts = DocumentFacts(fields={"cnpj_cpf_pagador": EXAMPLE_CNPJ})

        assert identify_document_condominium(self.document, facts) == self.other
        self.document.refresh_from_db()
        assert self.document.condominium == self.other
        assert len(self._events()) == 1

    def test_unrecognized_document_records_the_attempt(self) -> None:
        facts = DocumentFacts(raw_text="documento sem nada reconhecível")
        assert identify_document_condominium(self.document, facts) is None
        (event,) = self._events()
        assert event.payload["data"]["applied"] is False
        assert event.payload["data"]["reason"] == NO_CONDOMINIUM_REASON

    def test_tenant_without_condominiums_is_left_untouched(self) -> None:
        Condominium.objects.all().delete()
        facts = DocumentFacts(fields={"cnpj_cpf_pagador": EXAMPLE_CNPJ})
        assert identify_document_condominium(self.document, facts) is None
        assert not self.document.events.exists()

    def test_manual_choice_records_who_and_from_to(self) -> None:
        set_document_condominium(self.document, self.example, self.user)
        set_document_condominium(self.document, self.other, self.user)
        first, second = self._events()
        assert first.payload["data"]["previous_condominium"] is None
        assert second.payload["data"]["previous_condominium"]["id"] == str(
            self.example.id
        )
        assert second.payload["data"]["condominium"]["id"] == str(self.other.id)
        assert second.payload["data"]["identified_by"] == self.user.get_username()
        assert second.payload["data"]["method"] == "manual"


class RunClassificationTests(TenantAPITestCase):
    """identificar o condomínio e classificar, de ponta a ponta."""

    def setUp(self) -> None:
        super().setUp()
        self.example = Condominium.objects.create(
            name="Edifício Exemplo", cnpj=EXAMPLE_CNPJ
        )
        self.water = LedgerAccount.objects.create(
            condominium=self.example, code="2.1.01", name="Água"
        )
        SupplierRule.objects.create(
            condominium=self.example, supplier_tax_id=COMPESA, ledger_account=self.water
        )
        self.document = Document.objects.create(
            channel="manual", file_uri="local://documents/condos/doc/original"
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

    def test_identifies_then_classifies_and_records_both_events(self) -> None:
        classification = run_classification(self.document)

        assert classification.ledger_account == self.water
        self.document.refresh_from_db()
        assert self.document.condominium == self.example
        types = list(
            self.document.events.order_by("occurred_at").values_list(
                "event_type", flat=True
            )
        )
        assert types == ["document.condominium_identified", "document.classified"]

    def test_unidentified_document_gets_no_classification(self) -> None:
        ExtractionResult.objects.filter(document=self.document).update(fields={})
        assert run_classification(self.document) is None
        assert not DocumentClassification.objects.exists()

    def test_changing_the_condominium_drops_the_stale_account(self) -> None:
        user = get_user_model().objects.get(username="reviewer@condos.test")
        other = Condominium.objects.create(name="Edifício Outro", cnpj=OTHER_CNPJ)
        run_classification(self.document)

        set_document_condominium(self.document, other, user)
        assert classify_document(self.document, other) is None

        assert not DocumentClassification.objects.exists()
        removal = self.document.events.filter(event_type="document.classified").latest(
            "occurred_at"
        )
        data = removal.payload["data"]
        assert data["applied"] is True
        assert data["ledger_account"] is None
        assert data["previous_ledger_account"]["code"] == "2.1.01"
        assert data["reason"] == STALE_ACCOUNT_REASON

    def test_changing_the_condominium_reclassifies_in_the_new_plan(self) -> None:
        user = get_user_model().objects.get(username="reviewer@condos.test")
        other = Condominium.objects.create(name="Edifício Outro", cnpj=OTHER_CNPJ)
        other_water = LedgerAccount.objects.create(
            condominium=other, code="7.1", name="Água e esgoto"
        )
        SupplierRule.objects.create(
            condominium=other, supplier_tax_id=COMPESA, ledger_account=other_water
        )
        run_classification(self.document)

        set_document_condominium(self.document, other, user)
        classification = classify_document(self.document, other)

        assert classification.ledger_account == other_water
        assert DocumentClassification.objects.count() == 1


class DocumentCondominiumAPITests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.authenticate("reviewer")
        self.example = Condominium.objects.create(
            name="Edifício Exemplo", cnpj=EXAMPLE_CNPJ
        )
        self.water = LedgerAccount.objects.create(
            condominium=self.example, code="2.1.01", name="Água"
        )
        SupplierRule.objects.create(
            condominium=self.example, supplier_tax_id=COMPESA, ledger_account=self.water
        )
        self.document = Document.objects.create(
            channel="manual", file_uri="local://documents/condos/doc/original"
        )
        ExtractionResult.objects.create(
            document=self.document,
            schema_id="conta_de_agua",
            schema_version="v1",
            fields={"cnpj_emissor": "09.769.035/0001-64"},
        )
        self.url = reverse("document-condominium", args=[self.document.id])

    def _put(self, condominium_id: object):
        return self.client.put(
            self.url, {"condominium_id": str(condominium_id)}, format="json"
        )

    def test_setting_the_condominium_triggers_the_classification(self) -> None:
        response = self._put(self.example.id)
        assert response.status_code == 200
        body = response.json()
        assert body["condominium_id"] == str(self.example.id)
        assert body["classification"]["ledger_account_id"] == str(self.water.id)
        self.document.refresh_from_db()
        assert self.document.condominium == self.example
        event = self.document.events.get(event_type="document.condominium_identified")
        assert event.payload["data"]["identified_by"] == "reviewer@condos.test"

    def test_requires_documents_validate_permission(self) -> None:
        self.authenticate("operator")
        assert self._put(self.example.id).status_code == 403
        self.document.refresh_from_db()
        assert self.document.condominium is None

    def test_rejects_inactive_or_unknown_condominium(self) -> None:
        self.example.is_active = False
        self.example.save()
        assert self._put(self.example.id).status_code == 400
        assert self._put("00000000-0000-4000-8000-000000000000").status_code == 400

    def test_service_token_is_refused(self) -> None:
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer secret", HTTP_X_TENANT=self.tenant.slug
        )
        with self.settings(DOCUPARSE_INTERNAL_SERVICE_TOKEN="secret"):
            assert self._put(self.example.id).status_code == 403

    def test_condominium_with_documents_cannot_be_deleted(self) -> None:
        self._put(self.example.id)
        self.authenticate("tenantAdmin")
        response = self.client.delete(
            reverse("condominium-detail", args=[self.example.id])
        )
        assert response.status_code == 409
