"""Modelo PaymentProcess: regras de sugestão, API de leitura e documentos avulsos."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from condominiums.tests.base import TenantAPITestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from documents.models import Document, ExtractionResult, PaymentProcess
from documents.services.payment_matching import run_payment_matching
from documents.services.payment_processes import suggest_boletos

SUPPLIER = "09.769.035/0001-64"


class PaymentProcessTestCase(TenantAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.now = timezone.now()

    def _doc(self, fields: dict, hours_ago: float = 0, **extra) -> Document:
        document = Document.objects.create(
            channel="email",
            file_uri=f"local://documents/{uuid4()}/original",
            original_filename=f"{uuid4()}.pdf",
            received_at=self.now - timedelta(hours=hours_ago),
            **extra,
        )
        ExtractionResult.objects.create(
            document=document, schema_id="x", schema_version="v1", fields=fields
        )
        return document

    def invoice(self, amount="1000.00", **kw) -> Document:
        return self._doc({"cnpj_fornecedor": SUPPLIER, "valor_nota": amount}, **kw)

    def boleto(self, amount="1000.00", **kw) -> Document:
        return self._doc(
            {"cnpj_cpf_beneficiario": SUPPLIER, "valor_boleto": amount}, **kw
        )


class SuggestBoletosTests(PaymentProcessTestCase):
    def test_creates_one_pending_process_and_reuses_it(self) -> None:
        invoice = self.invoice()
        first, second = self.boleto("300.00"), self.boleto("300.00")

        a = suggest_boletos(invoice.id, [first.id])
        b = suggest_boletos(invoice.id, [second.id])

        assert a.id == b.id
        assert PaymentProcess.objects.count() == 1
        assert set(a.boletos.all()) == {first, second}

    def test_nothing_new_returns_none(self) -> None:
        invoice, boleto = self.invoice(), self.boleto()
        suggest_boletos(invoice.id, [boleto.id])

        assert suggest_boletos(invoice.id, [boleto.id]) is None

    def test_rejected_pair_is_not_suggested_again(self) -> None:
        invoice, boleto = self.invoice(), self.boleto()
        process = suggest_boletos(invoice.id, [boleto.id])
        process.status = PaymentProcess.Status.REJECTED
        process.save()

        assert suggest_boletos(invoice.id, [boleto.id]) is None
        assert PaymentProcess.objects.filter(status="PENDING").count() == 0

    def test_new_boleto_after_a_rejection_gets_a_new_pending_process(self) -> None:
        invoice, old, new = self.invoice(), self.boleto(), self.boleto()
        rejected = suggest_boletos(invoice.id, [old.id])
        rejected.status = PaymentProcess.Status.REJECTED
        rejected.save()

        fresh = suggest_boletos(invoice.id, [old.id, new.id])

        assert fresh.id != rejected.id
        assert list(fresh.boletos.all()) == [new]

    def test_boleto_confirmed_for_another_invoice_is_not_suggested(self) -> None:
        mine, other, boleto = self.invoice(), self.invoice(), self.boleto()
        taken = suggest_boletos(other.id, [boleto.id])
        taken.status = PaymentProcess.Status.CONFIRMED
        taken.save()

        assert suggest_boletos(mine.id, [boleto.id]) is None

    def test_boleto_pending_for_two_invoices_is_allowed(self) -> None:
        a, b, boleto = self.invoice(), self.invoice(), self.boleto()

        assert suggest_boletos(a.id, [boleto.id]) is not None
        assert suggest_boletos(b.id, [boleto.id]) is not None

    def test_new_boleto_for_a_confirmed_invoice_opens_a_pending_process(self) -> None:
        invoice, first, later = self.invoice(), self.boleto(), self.boleto()
        confirmed = suggest_boletos(invoice.id, [first.id])
        confirmed.status = PaymentProcess.Status.CONFIRMED
        confirmed.save()

        pending = suggest_boletos(invoice.id, [first.id, later.id])

        assert pending.status == PaymentProcess.Status.PENDING
        assert list(pending.boletos.all()) == [later]

    def test_database_allows_one_pending_and_one_confirmed_per_invoice(self) -> None:
        invoice = self.invoice()
        PaymentProcess.objects.create(invoice=invoice)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PaymentProcess.objects.create(invoice=invoice)
        PaymentProcess.objects.create(
            invoice=invoice, status=PaymentProcess.Status.CONFIRMED
        )
        PaymentProcess.objects.create(
            invoice=invoice, status=PaymentProcess.Status.REJECTED
        )
        PaymentProcess.objects.create(
            invoice=invoice, status=PaymentProcess.Status.REJECTED
        )


class StandaloneDocumentTests(PaymentProcessTestCase):
    def test_invoice_without_boleto_has_no_process_and_is_still_listed(self) -> None:
        invoice = self.invoice()
        run_payment_matching(invoice)

        assert not PaymentProcess.objects.exists()
        rows = self.client.get(reverse("processes-dashboard")).json()["results"]
        assert [r["id"] for r in rows] == [str(invoice.id)]
        assert rows[0]["payment_processes"] == []
        detail = self.client.get(reverse("document-detail", args=[invoice.id])).json()
        assert detail["payment_processes"] == []

    def test_deleting_the_only_boleto_drops_the_empty_pending_process(self) -> None:
        invoice, boleto = self.invoice(), self.boleto()
        suggest_boletos(invoice.id, [boleto.id])

        boleto.delete()

        assert not PaymentProcess.objects.exists()
        assert Document.objects.filter(pk=invoice.pk).exists()

    def test_deleting_one_of_two_boletos_keeps_the_process(self) -> None:
        invoice, a, b = self.invoice(), self.boleto(), self.boleto()
        suggest_boletos(invoice.id, [a.id, b.id])

        a.delete()

        assert PaymentProcess.objects.get().boletos.count() == 1


class PaymentProcessApiTests(PaymentProcessTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.invoice_doc = self.invoice("900.00", hours_ago=2)
        self.parcels = [self.boleto("300.00", hours_ago=h) for h in (1, 0)]
        self.process = suggest_boletos(
            self.invoice_doc.id, [p.id for p in self.parcels]
        )

    def test_list_returns_the_grouping_with_amounts(self) -> None:
        body = self.client.get(reverse("payment-processes")).json()

        assert body["count"] == 1
        item = body["results"][0]
        assert item["id"] == str(self.process.id)
        assert item["status"] == "PENDING" and item["origin"] == "AUTOMATIC"
        assert item["invoice"]["id"] == str(self.invoice_doc.id)
        assert item["invoice"]["tax_id"] == "09769035000164"
        assert item["invoice_amount"] == "900.00"
        assert [b["id"] for b in item["boletos"]] == [str(p.id) for p in self.parcels]
        assert item["boletos_total"] == "600.00"
        assert item["decided_by"] is None and item["decided_at"] is None

    def test_detail(self) -> None:
        response = self.client.get(
            reverse("payment-process-detail", args=[self.process.id])
        )

        assert response.status_code == 200
        assert response.json()["id"] == str(self.process.id)

    def test_filters(self) -> None:
        url = reverse("payment-processes")

        assert self.client.get(url, {"status": "CONFIRMED"}).json()["count"] == 0
        assert self.client.get(url, {"status": "PENDING"}).json()["count"] == 1
        assert self.client.get(url, {"origin": "MANUAL"}).json()["count"] == 0
        by_boleto = self.client.get(url, {"document_id": str(self.parcels[0].id)})
        assert by_boleto.json()["count"] == 1
        assert self.client.get(url, {"document_id": str(uuid4())}).json()["count"] == 0
        assert self.client.get(url, {"status": "nope"}).status_code == 400

    def test_documents_expose_their_processes_with_the_role(self) -> None:
        rows = {
            r["id"]: r["payment_processes"]
            for r in self.client.get(reverse("processes-dashboard")).json()["results"]
        }
        pid = str(self.process.id)
        assert rows[str(self.invoice_doc.id)] == [
            {"id": pid, "status": "PENDING", "role": "invoice"}
        ]
        assert rows[str(self.parcels[0].id)] == [
            {"id": pid, "status": "PENDING", "role": "boleto"}
        ]

    def test_rejected_processes_do_not_show_on_the_documents(self) -> None:
        self.process.status = PaymentProcess.Status.REJECTED
        self.process.save()

        detail = self.client.get(
            reverse("document-detail", args=[self.invoice_doc.id])
        ).json()
        assert detail["payment_processes"] == []

    def test_requires_authentication(self) -> None:
        self.client.credentials()

        assert self.client.get(reverse("payment-processes")).status_code in (401, 403)

    def test_decision_fields_are_serialized(self) -> None:
        user = get_user_model().objects.get(username="reviewer@condos.test")
        self.process.status = PaymentProcess.Status.CONFIRMED
        self.process.decided_by = user
        self.process.decided_at = timezone.now()
        self.process.save()

        item = self.client.get(reverse("payment-processes")).json()["results"][0]

        assert item["decided_by"] == "reviewer@condos.test"
        assert item["decided_at"]
