"""Modelo PaymentProcess: regras de sugestão, API de leitura e documentos avulsos."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from condominiums.tests.base import TenantAPITestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from events import validate_event

from documents.models import Document, DocumentEvent, ExtractionResult, PaymentProcess
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


class PaymentProcessDecisionTests(PaymentProcessTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.invoice_doc = self.invoice("900.00", hours_ago=2)
        self.parcels = [self.boleto("300.00", hours_ago=h) for h in (1, 0)]
        self.process = suggest_boletos(
            self.invoice_doc.id, [p.id for p in self.parcels]
        )
        self.user = get_user_model().objects.get(username="reviewer@condos.test")

    def _post(self, name: str, process=None, role: str = "reviewer"):
        self.authenticate(role)
        return self.client.post(
            reverse(name, args=[(process or self.process).id]), format="json"
        )

    def _events(self, event_type: str):
        return DocumentEvent.objects.filter(event_type=event_type)

    def test_automatic_match_stays_pending_until_someone_decides(self) -> None:
        self.process.refresh_from_db()

        assert self.process.status == PaymentProcess.Status.PENDING
        assert self.process.decided_by is None and self.process.decided_at is None
        assert not self._events("payment_process.confirmed").exists()

    def test_confirm_records_who_and_when_on_every_document(self) -> None:
        response = self._post("payment-process-confirm")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "CONFIRMED"
        assert body["decided_by"] == "reviewer@condos.test"
        events = self._events("payment_process.confirmed")
        assert events.count() == 3  # nota + dois boletos
        assert {e.document_id for e in events} == {
            self.invoice_doc.id,
            *(p.id for p in self.parcels),
        }
        payload = events.first().payload
        validate_event(payload)
        assert payload["data"]["decided_by"] == "reviewer@condos.test"
        assert payload["data"]["origin"] == "automatic"
        assert payload["data"]["process_id"] == str(self.process.id)
        assert sorted(payload["data"]["boleto_ids"]) == sorted(
            str(p.id) for p in self.parcels
        )
        self.process.refresh_from_db()
        assert self.process.decided_by == self.user
        assert events.first().occurred_at == self.process.decided_at

    def test_reject_returns_documents_to_the_pool_and_records_the_event(self) -> None:
        response = self._post("payment-process-reject")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "REJECTED"
        assert body["decided_by"] == "reviewer@condos.test"
        assert body["decided_at"]
        events = self._events("payment_process.rejected")
        assert events.count() == 3
        payload = events.first().payload
        validate_event(payload)
        assert payload["data"]["decided_by"] == "reviewer@condos.test"
        detail = self.client.get(
            reverse("document-detail", args=[self.parcels[0].id])
        ).json()
        assert detail["payment_processes"] == []
        # a rejeição não volta sozinha no próximo matching
        run_payment_matching(self.parcels[0])
        assert not PaymentProcess.objects.filter(status="PENDING").exists()

    def test_a_decided_process_cannot_be_decided_again(self) -> None:
        self._post("payment-process-confirm")

        for name in ("payment-process-confirm", "payment-process-reject"):
            response = self._post(name)
            assert response.status_code == 409
            assert response.json()["code"] == "not_pending"
        assert self._events("payment_process.confirmed").count() == 3

    def test_decision_requires_the_validate_permission(self) -> None:
        response = self._post("payment-process-confirm", role="operator")

        assert response.status_code == 403
        self.process.refresh_from_db()
        assert self.process.status == PaymentProcess.Status.PENDING

    def test_unknown_process_is_404(self) -> None:
        self.authenticate("reviewer")
        url = reverse("payment-process-confirm", args=[uuid4()])

        assert self.client.post(url).status_code == 404

    def test_confirming_takes_the_boleto_out_of_other_pending_processes(self) -> None:
        other_invoice = self.invoice("900.00", hours_ago=2)
        shared = self.parcels[0]
        other = suggest_boletos(other_invoice.id, [shared.id])
        assert other is not None

        self._post("payment-process-confirm")

        assert not PaymentProcess.objects.filter(pk=other.pk).exists()

    def test_other_pending_process_keeps_its_remaining_boletos(self) -> None:
        other_invoice = self.invoice("900.00", hours_ago=2)
        extra = self.boleto("100.00")
        other = suggest_boletos(other_invoice.id, [self.parcels[0].id, extra.id])

        self._post("payment-process-confirm")

        assert list(other.boletos.all()) == [extra]

    def test_boleto_confirmed_elsewhere_blocks_the_confirmation(self) -> None:
        other_invoice = self.invoice("900.00", hours_ago=2)
        other = suggest_boletos(other_invoice.id, [self.parcels[0].id])
        other.status = PaymentProcess.Status.CONFIRMED
        other.save()
        # monta o pendente à força, como uma corrida entre dois operadores
        self.process.boletos.add(self.parcels[0])

        response = self._post("payment-process-confirm")

        assert response.status_code == 409
        assert response.json()["code"] == "boleto_taken"
        self.process.refresh_from_db()
        assert self.process.status == PaymentProcess.Status.PENDING

    def test_late_boleto_is_merged_into_the_confirmed_process(self) -> None:
        self._post("payment-process-confirm")
        late = self.boleto("300.00")
        pending = suggest_boletos(self.invoice_doc.id, [late.id])
        assert pending.id != self.process.id

        response = self._post("payment-process-confirm", process=pending)

        assert response.status_code == 200
        assert response.json()["id"] == str(self.process.id)
        assert not PaymentProcess.objects.filter(pk=pending.pk).exists()
        self.process.refresh_from_db()
        assert self.process.boletos.count() == 3
        assert (
            PaymentProcess.objects.filter(
                invoice=self.invoice_doc, status="CONFIRMED"
            ).count()
            == 1
        )

    def test_empty_process_cannot_be_confirmed(self) -> None:
        empty = PaymentProcess.objects.create(invoice=self.invoice())

        response = self._post("payment-process-confirm", process=empty)

        assert response.status_code == 422
        assert response.json()["code"] == "no_boletos"


class ManualMatchTests(PaymentProcessTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.invoice_doc = self.invoice("900.00", hours_ago=60)
        self.boleto_doc = self.boleto("300.00")

    def _candidates(self, kind: str, **params):
        self.authenticate("operator")
        return self.client.get(reverse("payment-candidates"), {"kind": kind, **params})

    def _create(self, invoice=None, boletos=None, role: str = "reviewer"):
        self.authenticate(role)
        chosen = [self.boleto_doc] if boletos is None else boletos
        return self.client.post(
            reverse("payment-process-create"),
            {
                "invoice_id": str((invoice or self.invoice_doc).id),
                "boleto_ids": [str(b.id) for b in chosen],
            },
            format="json",
        )

    def test_pool_lists_documents_without_a_match_by_kind(self) -> None:
        other_kind = self._doc({"cnpj_emissor": SUPPLIER, "valor_total": "10"})

        invoices = self._candidates("invoice").json()
        boletos = self._candidates("boleto").json()

        assert [d["id"] for d in invoices["results"]] == [str(self.invoice_doc.id)]
        assert [d["id"] for d in boletos["results"]] == [str(self.boleto_doc.id)]
        assert str(other_kind.id) not in {d["id"] for d in invoices["results"]}
        row = boletos["results"][0]
        assert row["amount"] == "300.00" and row["tax_id"] == "09769035000164"

    def test_pool_keeps_documents_whose_values_could_not_be_read(self) -> None:
        truncated = self._doc(
            {"cnpj_cpf_beneficiario": "32.435.490/0001-", "valor_boleto": "1100,00"}
        )

        rows = self._candidates("boleto").json()["results"]

        listed = next(r for r in rows if r["id"] == str(truncated.id))
        assert listed["tax_id"] is None  # sem CNPJ válido: o operador pareia à mão

    def test_pool_drops_documents_in_pending_or_confirmed_processes(self) -> None:
        suggest_boletos(self.invoice_doc.id, [self.boleto_doc.id])

        assert self._candidates("invoice").json()["count"] == 0
        assert self._candidates("boleto").json()["count"] == 0

    def test_documents_return_to_the_pool_after_a_rejection(self) -> None:
        process = suggest_boletos(self.invoice_doc.id, [self.boleto_doc.id])
        process.status = PaymentProcess.Status.REJECTED
        process.save()

        assert self._candidates("invoice").json()["count"] == 1
        assert self._candidates("boleto").json()["count"] == 1

    def test_pool_search_and_kind_validation(self) -> None:
        self.invoice_doc.original_filename = "nota-especial.pdf"
        self.invoice_doc.save()

        assert self._candidates("invoice", search="especial").json()["count"] == 1
        assert self._candidates("invoice", search="nada-aqui").json()["count"] == 0
        assert self._candidates("outro").status_code == 400

    def test_manual_selection_creates_a_pending_manual_process(self) -> None:
        response = self._create()

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "PENDING" and body["origin"] == "MANUAL"
        assert body["invoice"]["id"] == str(self.invoice_doc.id)
        assert [b["id"] for b in body["boletos"]] == [str(self.boleto_doc.id)]
        assert body["decided_by"] is None

    def test_manual_selection_goes_through_the_same_confirmation(self) -> None:
        process_id = self._create().json()["id"]

        self.authenticate("reviewer")
        confirm = self.client.post(
            reverse("payment-process-confirm", args=[process_id])
        )

        assert confirm.status_code == 200
        assert confirm.json()["status"] == "CONFIRMED"
        event = DocumentEvent.objects.filter(
            event_type="payment_process.confirmed"
        ).first()
        assert event.payload["data"]["origin"] == "manual"
        assert event.payload["data"]["decided_by"] == "reviewer@condos.test"

    def test_manual_selection_accepts_values_the_automatic_rule_would_refuse(
        self,
    ) -> None:
        bigger = self.boleto("5000.00")  # maior que a nota: o automático não casaria

        assert self._create(boletos=[bigger]).status_code == 201

    def test_undo_before_confirming_returns_documents_to_the_pool(self) -> None:
        process_id = self._create().json()["id"]
        assert self._candidates("invoice").json()["count"] == 0

        self.authenticate("reviewer")
        undo = self.client.post(reverse("payment-process-undo", args=[process_id]))

        assert undo.status_code == 204
        assert not PaymentProcess.objects.filter(pk=process_id).exists()
        assert self._candidates("invoice").json()["count"] == 1
        assert self._candidates("boleto").json()["count"] == 1

    def test_undo_refuses_confirmed_and_automatic_processes(self) -> None:
        automatic = suggest_boletos(self.invoice_doc.id, [self.boleto_doc.id])
        self.authenticate("reviewer")
        assert (
            self.client.post(
                reverse("payment-process-undo", args=[automatic.id])
            ).json()["code"]
            == "not_manual"
        )

        manual_invoice, manual_boleto = self.invoice(), self.boleto()
        manual_id = self._create(manual_invoice, [manual_boleto]).json()["id"]
        self.authenticate("reviewer")
        self.client.post(reverse("payment-process-confirm", args=[manual_id]))
        response = self.client.post(reverse("payment-process-undo", args=[manual_id]))

        assert response.status_code == 409
        assert response.json()["code"] == "not_pending"

    def test_rejects_wrong_kinds_and_empty_selection(self) -> None:
        assert self._create(boletos=[self.invoice()]).status_code == 400
        assert self._create(invoice=self.boleto_doc).status_code == 400
        assert self._create(boletos=[]).status_code == 422

    def test_rejects_unavailable_documents(self) -> None:
        self._create()

        again = self._create()  # a nota já tem um agrupamento pendente
        assert again.status_code == 409 and again.json()["code"] == "invoice_busy"

        other_invoice = self.invoice()
        taken = self._create(other_invoice)  # o boleto já está no pendente
        assert taken.status_code == 409
        assert taken.json()["code"] == "boleto_unavailable"

    def test_unknown_document_and_bad_payload(self) -> None:
        ghost = Document(id=uuid4())
        assert self._create(invoice=ghost).status_code == 404
        self.authenticate("reviewer")
        url = reverse("payment-process-create")
        assert self.client.post(url, {}, format="json").status_code == 400
        bad = {"invoice_id": "not-a-uuid", "boleto_ids": ["x"]}
        assert self.client.post(url, bad, format="json").status_code == 400

    def test_requires_the_validate_permission_but_the_pool_only_inbox_view(
        self,
    ) -> None:
        assert self._create(role="operator").status_code == 403
        self.authenticate("operator")
        undo = self.client.post(reverse("payment-process-undo", args=[uuid4()]))
        assert undo.status_code == 403
        assert self._candidates("invoice").status_code == 200
