"""Casamento NF + boleto por CNPJ e valor, disparado quando a extração chega."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from catalog.models import SchemaConfig
from condominiums.tests.base import TenantAPITestCase
from django.test import override_settings
from django.utils import timezone as dj_timezone

from documents.models import Document, ExtractionResult, PaymentProcess
from documents.services.ocr_processor import (
    auto_extract_after_ocr,
    run_langextract_for_document,
)
from documents.services.payment_matching import (
    PaymentCandidate,
    build_candidate,
    is_match,
    parse_amount,
    run_payment_matching,
    run_payment_matching_safely,
)

SUPPLIER = "09769035000164"
OTHER_SUPPLIER = "11222333000181"
SUPPLIER_MASKED = "09.769.035/0001-64"


def _invoice(amount: str, tax_id: str = SUPPLIER) -> PaymentCandidate:
    return PaymentCandidate("nf", "invoice", tax_id, Decimal(amount))


def _boleto(amount: str, tax_id: str = SUPPLIER) -> PaymentCandidate:
    return PaymentCandidate("bol", "boleto", tax_id, Decimal(amount))


class MatchRuleTests(TenantAPITestCase):
    """Os quatro casos do ticket, sem banco."""

    def test_same_cnpj_and_same_amount_matches(self) -> None:
        assert is_match(_invoice("1000.00"), _boleto("1000.00"))

    def test_same_cnpj_and_smaller_boleto_matches(self) -> None:
        assert is_match(_invoice("1000.00"), _boleto("400.00"))

    def test_same_cnpj_and_larger_boleto_does_not_match(self) -> None:
        assert not is_match(_invoice("1000.00"), _boleto("1000.01"))

    def test_different_cnpj_does_not_match(self) -> None:
        assert not is_match(_invoice("1000.00"), _boleto("1000.00", OTHER_SUPPLIER))


class CandidateTests(TenantAPITestCase):
    def test_invoice_uses_supplier_cnpj_and_total(self) -> None:
        candidate = build_candidate(
            "id", {"cnpj_fornecedor": SUPPLIER_MASKED, "valor_nota": "1.470,15"}
        )
        assert candidate == PaymentCandidate(
            "id", "invoice", SUPPLIER, Decimal("1470.15")
        )

    def test_boleto_uses_beneficiary_cnpj_and_falls_back_to_document_value(
        self,
    ) -> None:
        candidate = build_candidate(
            "id", {"cnpj_cpf_beneficiario": SUPPLIER, "valor_documento": 99.9}
        )
        assert candidate == PaymentCandidate("id", "boleto", SUPPLIER, Decimal("99.90"))

    def test_unusable_documents_have_no_candidate(self) -> None:
        for fields in (
            {"cnpj_fornecedor": SUPPLIER},  # sem valor
            {"cnpj_fornecedor": SUPPLIER, "valor_nota": "0"},
            {"cnpj_fornecedor": "11111111111111", "valor_nota": "10"},  # CNPJ inválido
            {"cnpj_cpf_beneficiario": "52998224725", "valor_boleto": "10"},  # CPF
            {"cnpj_cpf_pagador": SUPPLIER, "valor_boleto": "10"},  # outro tipo
            {"cnpj_fornecedor": None, "valor_nota": "10"},
        ):
            assert build_candidate("id", fields) is None, fields

    def test_parse_amount_formats(self) -> None:
        assert parse_amount("R$ 1.470,15") == Decimal("1470.15")
        assert parse_amount("1470.15") == Decimal("1470.15")
        assert parse_amount(1470) == Decimal("1470.00")
        assert parse_amount("abc") is None
        assert parse_amount(True) is None
        assert parse_amount(None) is None


class PaymentMatchingTests(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.now = dj_timezone.now()

    def _doc(self, fields: dict, *, hours_ago: float = 0, **extra) -> Document:
        document = Document.objects.create(
            channel="email",
            file_uri=f"local://documents/{uuid4()}/original",
            received_at=self.now - timedelta(hours=hours_ago),
            **extra,
        )
        ExtractionResult.objects.create(
            document=document, schema_id="x", schema_version="v1", fields=fields
        )
        return document

    def _invoice(self, amount="1000.00", tax_id=SUPPLIER, **kw) -> Document:
        return self._doc({"cnpj_fornecedor": tax_id, "valor_nota": amount}, **kw)

    def _boleto(self, amount="1000.00", tax_id=SUPPLIER, **kw) -> Document:
        return self._doc(
            {"cnpj_cpf_beneficiario": tax_id, "valor_boleto": amount}, **kw
        )

    def _pairs(self) -> set[tuple]:
        return {
            (process.invoice_id, boleto.id)
            for process in PaymentProcess.objects.prefetch_related("boletos")
            for boleto in process.boletos.all()
        }

    def test_boleto_arriving_after_the_invoice_matches(self) -> None:
        invoice = self._invoice(hours_ago=2)
        boleto = self._boleto()
        touched = run_payment_matching(boleto)
        assert [p.invoice_id for p in touched] == [invoice.id]
        process = touched[0]
        assert process.status == PaymentProcess.Status.PENDING
        assert process.origin == PaymentProcess.Origin.AUTOMATIC
        assert list(process.boletos.all()) == [boleto]
        assert process.decided_by is None and process.decided_at is None

    def test_invoice_arriving_after_the_boleto_matches(self) -> None:
        boleto = self._boleto(hours_ago=2)
        invoice = self._invoice()
        run_payment_matching(invoice)
        assert self._pairs() == {(invoice.id, boleto.id)}

    def test_smaller_boleto_matches(self) -> None:
        invoice = self._invoice("1000.00", hours_ago=1)
        boleto = self._boleto("250.00")
        run_payment_matching(boleto)
        assert self._pairs() == {(invoice.id, boleto.id)}

    def test_larger_boleto_does_not_match(self) -> None:
        self._invoice("1000.00", hours_ago=1)
        run_payment_matching(self._boleto("1000.01"))
        assert not PaymentProcess.objects.exists()

    def test_different_cnpj_does_not_match(self) -> None:
        self._invoice(tax_id=OTHER_SUPPLIER, hours_ago=1)
        run_payment_matching(self._boleto())
        assert not PaymentProcess.objects.exists()

    def test_installments_share_one_pending_process(self) -> None:
        invoice = self._invoice("900.00", hours_ago=5)
        for hours in (3, 2, 1):
            run_payment_matching(self._boleto("300.00", hours_ago=hours))
        process = PaymentProcess.objects.get(invoice=invoice)
        assert process.boletos.count() == 3

    def test_installments_one_invoice_many_boletos(self) -> None:
        invoice = self._invoice("900.00", hours_ago=5)
        parcels = [self._boleto("300.00", hours_ago=h) for h in (3, 2, 1)]
        for parcel in parcels:
            run_payment_matching(parcel)
        assert self._pairs() == {(invoice.id, p.id) for p in parcels}

    def test_installments_arriving_in_any_order_give_the_same_pairs(self) -> None:
        parcels = [self._boleto("300.00", hours_ago=h) for h in (5, 4, 3)]
        for parcel in parcels:
            run_payment_matching(parcel)
        assert not PaymentProcess.objects.exists()
        invoice = self._invoice("900.00")
        touched = run_payment_matching(invoice)
        assert len(touched) == 1  # um só processo com as três parcelas
        assert touched[0].boletos.count() == 3
        assert self._pairs() == {(invoice.id, p.id) for p in parcels}

    def test_one_boleto_with_many_invoices(self) -> None:
        boleto = self._boleto("500.00", hours_ago=0)
        invoices = [self._invoice("500.00", hours_ago=h) for h in (1, 2)]
        run_payment_matching(boleto)
        assert self._pairs() == {(i.id, boleto.id) for i in invoices}

    def test_each_boleto_is_checked_alone_not_by_the_sum(self) -> None:
        invoice = self._invoice("1000.00", hours_ago=3)
        big = [self._boleto("800.00", hours_ago=h) for h in (2, 1)]
        for boleto in big:
            run_payment_matching(boleto)
        assert self._pairs() == {(invoice.id, b.id) for b in big}

    def test_two_invoices_never_match_each_other(self) -> None:
        self._invoice(hours_ago=1)
        run_payment_matching(self._invoice())
        assert not PaymentProcess.objects.exists()

    def test_two_boletos_never_match_each_other(self) -> None:
        self._boleto(hours_ago=1)
        run_payment_matching(self._boleto())
        assert not PaymentProcess.objects.exists()

    def test_candidate_outside_the_window_is_ignored(self) -> None:
        self._invoice(hours_ago=73)
        run_payment_matching(self._boleto())
        assert not PaymentProcess.objects.exists()

    def test_candidate_inside_the_window_is_found(self) -> None:
        invoice = self._invoice(hours_ago=71)
        boleto = self._boleto()
        run_payment_matching(boleto)
        assert self._pairs() == {(invoice.id, boleto.id)}

    @override_settings(PAYMENT_MATCH_WINDOW_HOURS=6)
    def test_window_is_configurable(self) -> None:
        self._invoice(hours_ago=7)
        near = self._invoice(hours_ago=5)
        boleto = self._boleto()
        run_payment_matching(boleto)
        assert self._pairs() == {(near.id, boleto.id)}

    def test_rejected_documents_are_not_candidates(self) -> None:
        self._invoice(hours_ago=1, status=Document.Status.REJECTED)
        run_payment_matching(self._boleto())
        assert not PaymentProcess.objects.exists()

    def test_running_twice_does_not_duplicate(self) -> None:
        self._invoice(hours_ago=1)
        boleto = self._boleto()
        assert len(run_payment_matching(boleto)) == 1
        assert run_payment_matching(boleto) == []
        assert PaymentProcess.objects.count() == 1

    def test_operator_edited_value_wins_over_the_original_extraction(self) -> None:
        from documents.models import ExtractionFieldVersion

        invoice = self._invoice("1000.00", hours_ago=1)
        ExtractionFieldVersion.objects.create(
            document=invoice,
            version_number=1,
            source_type=ExtractionFieldVersion.SourceType.MANUAL_EDIT,
            fields={
                "cnpj_fornecedor": {"value": SUPPLIER, "confidence": 1},
                "valor_nota": {"value": "100.00", "confidence": 1},
            },
            is_active=True,
        )
        run_payment_matching(self._boleto("500.00"))
        assert not PaymentProcess.objects.exists()

    def test_unrelated_document_is_a_noop(self) -> None:
        self._invoice(hours_ago=1)
        other = self._doc({"cnpj_emissor": SUPPLIER, "valor_total": "10"})
        assert run_payment_matching(other) == []

    def test_safe_version_swallows_errors(self) -> None:
        boleto = self._boleto()
        with patch(
            "documents.services.payment_matching.candidate_for",
            side_effect=RuntimeError("boom"),
        ):
            assert run_payment_matching_safely(boleto) == []


class PipelineTriggerTests(TenantAPITestCase):
    """O casamento roda sozinho nos pontos do pipeline que gravam a extração."""

    def setUp(self) -> None:
        super().setUp()
        self.invoice = Document.objects.create(
            channel="email", file_uri="local://documents/nf/original"
        )
        ExtractionResult.objects.create(
            document=self.invoice,
            schema_id="nota_fiscal_default",
            schema_version="v1",
            fields={
                "cnpj_fornecedor": {"value": SUPPLIER_MASKED, "confidence": 0.9},
                "valor_nota": {"value": "1000.00", "confidence": 0.9},
            },
        )
        self.boleto = Document.objects.create(
            channel="email",
            file_uri="local://documents/bol/original",
            raw_text_uri="local://documents/bol/ocr/raw_text.json",
        )
        self.schema, _ = SchemaConfig.objects.get_or_create(
            schema_id="boleto_default", version="v1", defaults={"definition": {}}
        )
        self.boleto_fields = {
            "cnpj_cpf_beneficiario": SUPPLIER_MASKED,
            "valor_boleto": "400.00",
        }

    def _assert_matched(self) -> None:
        process = PaymentProcess.objects.get()
        assert process.invoice_id == self.invoice.id
        assert list(process.boletos.all()) == [self.boleto]

    def _langextract(self) -> None:
        client = patch("documents.services.ocr_processor.LangExtractClient")
        started = client.start()
        started.return_value.extract_with_schema.return_value = {
            "fields": self.boleto_fields,
            "confidence": 0.9,
        }
        self.addCleanup(client.stop)

    def _storage(self):
        storage = MagicMock()
        storage.get_bytes.return_value = b'{"raw_text": "boleto"}'
        return patch(
            "documents.services.ocr_processor.get_storage", return_value=storage
        )

    def test_automatic_extraction_after_ocr_matches(self) -> None:
        self._langextract()
        with (
            self._storage(),
            patch(
                "documents.services.ocr_processor._resolve_schema_for_extraction",
                return_value=self.schema,
            ),
        ):
            auto_extract_after_ocr(self.boleto)
        self._assert_matched()

    def test_manual_extraction_matches(self) -> None:
        self._langextract()
        with self._storage():
            run_langextract_for_document(self.boleto.id, self.schema.id)
        self._assert_matched()

    def test_matching_failure_does_not_break_the_extraction(self) -> None:
        self._langextract()
        with (
            self._storage(),
            patch(
                "documents.services.ocr_processor._resolve_schema_for_extraction",
                return_value=self.schema,
            ),
            patch(
                "documents.services.payment_matching.candidate_for",
                side_effect=RuntimeError("boom"),
            ),
        ):
            auto_extract_after_ocr(self.boleto)

        self.boleto.refresh_from_db()
        assert self.boleto.status == Document.Status.VALIDATION_PENDING
        assert ExtractionResult.objects.filter(document=self.boleto).exists()
        assert not PaymentProcess.objects.exists()
