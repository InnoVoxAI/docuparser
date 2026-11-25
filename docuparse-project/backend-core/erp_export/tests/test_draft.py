"""Montagem e validação da despesa: cada regra tem a sua mensagem."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.test import TestCase
from documents.models import PaymentProcess

from erp_export.draft import build_draft, parse_date
from erp_export.errors import DraftInvalid

from .helpers import (
    CHART_ERP_ID,
    CONDOMINIUM_ERP_ID,
    SUPPLIER_CNPJ,
    boleto_fields,
    invoice_fields,
    make_document,
    make_tenant,
    make_world,
)


def codes(invalid: DraftInvalid) -> list[str]:
    return [error.code for error in invalid.errors]


def confirmed_process(invoice, *boletos):
    process = PaymentProcess.objects.create(
        invoice=invoice, status=PaymentProcess.Status.CONFIRMED
    )
    process.boletos.set(boletos)
    return process


class ParseDateTests(TestCase):
    def test_accepts_iso_and_brazilian_dates_and_rejects_garbage(self):
        assert parse_date("2026-07-20") == date(2026, 7, 20)
        assert parse_date("20/07/2026") == date(2026, 7, 20)
        assert parse_date("20/07/2026 10:30:00") == date(2026, 7, 20)
        assert parse_date("31/02/2026") is None
        assert parse_date("") is None
        assert parse_date(None) is None


class BoletoDraftTests(TestCase):
    def setUp(self):
        make_tenant("tenant-draft-boleto")
        self.world = make_world()

    def test_standalone_boleto_builds_a_single_installment(self):
        document = make_document(self.world, boleto_fields())
        draft = build_draft(document)
        assert draft.kind == "boleto"
        assert draft.condominium_external_id == CONDOMINIUM_ERP_ID
        assert draft.chart_external_id == CHART_ERP_ID
        assert draft.account_code == "2.1.02"
        assert draft.supplier_tax_id == SUPPLIER_CNPJ
        assert draft.amount == Decimal("1000.00")
        assert [(i.amount, i.due_date) for i in draft.installments] == [
            (Decimal("1000.00"), date(2026, 7, 20))
        ]

    def test_boleto_that_belongs_to_a_confirmed_process_does_not_create_its_own_expense(
        self,
    ):
        invoice = make_document(self.world, invoice_fields())
        boleto = make_document(self.world, boleto_fields())
        confirmed_process(invoice, boleto)
        with pytest.raises(DraftInvalid) as raised:
            build_draft(boleto)
        assert codes(raised.value) == ["covered_by_invoice"]

    def test_a_pending_process_does_not_cover_the_boleto(self):
        invoice = make_document(self.world, invoice_fields())
        boleto = make_document(self.world, boleto_fields())
        process = PaymentProcess.objects.create(invoice=invoice)  # PENDING
        process.boletos.set([boleto])
        assert build_draft(boleto).kind == "boleto"


class InvoiceDraftTests(TestCase):
    def setUp(self):
        make_tenant("tenant-draft-invoice")
        self.world = make_world()

    def test_invoice_without_a_confirmed_process_has_no_due_date(self):
        document = make_document(self.world, invoice_fields())
        with pytest.raises(DraftInvalid) as raised:
            build_draft(document)
        assert codes(raised.value) == ["due_date_missing"]
        assert "processo de pagamento" in raised.value.errors[0].message

    def test_invoice_takes_installments_from_the_confirmed_process(self):
        invoice = make_document(self.world, invoice_fields(valor_nota="2000,00"))
        first = make_document(
            self.world,
            boleto_fields(valor_boleto="1000,00", data_vencimento="2026-08-10"),
        )
        second = make_document(
            self.world,
            boleto_fields(valor_boleto="1000,00", data_vencimento="2026-07-10"),
        )
        confirmed_process(invoice, first, second)
        draft = build_draft(invoice)
        assert draft.kind == "invoice"
        assert draft.document_number == "123"
        assert draft.issue_date == date(2026, 7, 1)
        # Ordenadas por vencimento.
        assert [i.due_date for i in draft.installments] == [
            date(2026, 7, 10),
            date(2026, 8, 10),
        ]
        assert draft.amount == Decimal("2000.00")

    def test_boletos_that_do_not_add_up_to_the_invoice_are_flagged(self):
        invoice = make_document(self.world, invoice_fields(valor_nota="2000,00"))
        only = make_document(self.world, boleto_fields(valor_boleto="1000,00"))
        confirmed_process(invoice, only)
        with pytest.raises(DraftInvalid) as raised:
            build_draft(invoice)
        assert codes(raised.value) == ["amounts_diverge"]
        assert "1000.00" in raised.value.errors[0].message
        assert "2000.00" in raised.value.errors[0].message

    def test_a_boleto_without_due_date_or_amount_is_named_in_the_error(self):
        invoice = make_document(self.world, invoice_fields())
        bad = make_document(
            self.world,
            boleto_fields(data_vencimento="", valor_boleto=""),
            filename="boleto-ruim.pdf",
        )
        confirmed_process(invoice, bad)
        with pytest.raises(DraftInvalid) as raised:
            build_draft(invoice)
        assert set(codes(raised.value)) == {"amount_missing", "due_date_missing"}
        assert all("boleto-ruim.pdf" in e.message for e in raised.value.errors)


class ValidationRuleTests(TestCase):
    def setUp(self):
        make_tenant("tenant-draft-rules")

    def draft_errors(self, world, fields=None, **kwargs):
        document = make_document(world, fields or boleto_fields(), **kwargs)
        with pytest.raises(DraftInvalid) as raised:
            build_draft(document)
        return raised.value

    def test_condominium_not_identified(self):
        world = make_world()
        document = make_document(world, boleto_fields())
        document.condominium = None
        document.save()
        with pytest.raises(DraftInvalid) as raised:
            build_draft(document)
        assert "condominium_missing" in codes(raised.value)

    def test_condominium_not_linked_to_the_erp(self):
        invalid = self.draft_errors(make_world(linked=False))
        assert "condominium_not_linked" in codes(invalid)
        assert "Edifício Exemplo" in invalid.errors[0].message

    def test_account_missing(self):
        invalid = self.draft_errors(make_world(), classified=False)
        assert codes(invalid) == ["account_missing"]

    def test_account_outside_the_condominium_chart(self):
        from accounting.models import (
            ChartOfAccounts,
            DocumentClassification,
            LedgerAccount,
        )

        world = make_world()
        document = make_document(world, boleto_fields(), classified=False)
        other_chart = ChartOfAccounts.objects.create(
            name="Outro", external_id="88", external_source="superlogica"
        )
        stray = LedgerAccount.objects.create(chart=other_chart, code="9.9", name="Fora")
        DocumentClassification.objects.create(
            document=document,
            ledger_account=stray,
            origin=DocumentClassification.Origin.MANUAL,
        )
        with pytest.raises(DraftInvalid) as raised:
            build_draft(document)
        assert "account_outside_chart" in codes(raised.value)
        assert "9.9" in raised.value.errors[0].message

    def test_chart_not_linked_to_the_erp(self):
        world = make_world()
        world["chart"].external_id = ""
        world["chart"].save()
        invalid = self.draft_errors(world)
        assert "account_not_linked" in codes(invalid)

    def test_invalid_supplier_tax_id(self):
        invalid = self.draft_errors(
            make_world(), boleto_fields(cnpj_cpf_beneficiario="11111111111111")
        )
        assert codes(invalid) == ["supplier_tax_id_invalid"]

    def test_missing_amount_and_due_date(self):
        invalid = self.draft_errors(
            make_world(), boleto_fields(valor_boleto="", data_vencimento="")
        )
        assert set(codes(invalid)) == {"amount_missing", "due_date_missing"}

    def test_zero_amount_counts_as_missing(self):
        invalid = self.draft_errors(make_world(), boleto_fields(valor_boleto="0,00"))
        assert "amount_missing" in codes(invalid)

    def test_all_problems_are_reported_at_once(self):
        world = make_world(linked=False)
        invalid = self.draft_errors(
            world,
            boleto_fields(
                cnpj_cpf_beneficiario="", valor_boleto="", data_vencimento=""
            ),
            classified=False,
        )
        assert set(codes(invalid)) >= {
            "condominium_not_linked",
            "account_missing",
            "supplier_tax_id_invalid",
            "amount_missing",
            "due_date_missing",
        }

    def test_a_document_that_is_neither_invoice_nor_boleto_is_not_supported(self):
        invalid = self.draft_errors(make_world(), {"qualquer": "coisa"})
        assert codes(invalid) == ["document_not_supported"]

    def test_every_error_has_a_portuguese_message(self):
        invalid = self.draft_errors(
            make_world(linked=False), boleto_fields(valor_boleto=""), classified=False
        )
        for error in invalid.errors:
            assert error.message and error.message[0].isupper()


class FingerprintTests(TestCase):
    def setUp(self):
        make_tenant("tenant-draft-fp")
        self.world = make_world()

    def test_fingerprint_changes_when_what_goes_to_the_erp_changes(self):
        document = make_document(self.world, boleto_fields())
        before = build_draft(document).fingerprint()
        assert build_draft(document).fingerprint() == before

        fields = document.extraction_result.fields
        fields["valor_boleto"] = {"value": "1001,00", "confidence": 1.0}
        document.extraction_result.fields = fields
        document.extraction_result.save()
        assert build_draft(document).fingerprint() != before
