"""Serialização dos processos de pagamento para o frontend."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db.models import Q
from rest_framework import serializers

from documents.models import Document, PaymentProcess
from documents.services.payment_matching import candidate_for


def _money(value: Decimal | None) -> str | None:
    return None if value is None else f"{value:.2f}"


class PaymentDocumentSerializer(serializers.ModelSerializer):
    """Documento dentro de um processo, com o CNPJ e o valor usados no casamento."""

    tax_id = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "original_filename",
            "document_type",
            "status",
            "channel",
            "source_thread_id",
            "received_at",
            "tax_id",
            "amount",
        ]

    def _candidate(self, obj: Document):
        cache = self.context.setdefault("_candidates", {})
        if obj.pk not in cache:
            cache[obj.pk] = candidate_for(obj)
        return cache[obj.pk]

    def get_tax_id(self, obj: Document) -> str | None:
        candidate = self._candidate(obj)
        return candidate.tax_id if candidate else None

    def get_amount(self, obj: Document) -> str | None:
        candidate = self._candidate(obj)
        return _money(candidate.amount) if candidate else None


class PaymentProcessSerializer(serializers.ModelSerializer):
    invoice = PaymentDocumentSerializer(read_only=True)
    boletos = PaymentDocumentSerializer(many=True, read_only=True)
    decided_by = serializers.SerializerMethodField()

    class Meta:
        model = PaymentProcess
        fields = [
            "id",
            "status",
            "origin",
            "invoice",
            "boletos",
            "decided_by",
            "decided_at",
            "created_at",
            "updated_at",
        ]

    def get_decided_by(self, obj: PaymentProcess) -> str | None:
        return obj.decided_by.get_username() if obj.decided_by else None

    def to_representation(self, instance: PaymentProcess) -> dict[str, Any]:
        data = super().to_representation(instance)
        data["boletos"] = sorted(data["boletos"], key=lambda b: b["received_at"])
        amounts = [Decimal(b["amount"]) for b in data["boletos"] if b["amount"]]
        data["invoice_amount"] = data["invoice"]["amount"]
        data["boletos_total"] = _money(sum(amounts, Decimal("0"))) if amounts else None
        return data


def payment_process_refs(
    document_ids: Iterable[UUID],
) -> dict[UUID, list[dict[str, str]]]:
    """Processos de cada documento (como nota ou como boleto), sem os rejeitados.

    Documento fora de qualquer processo não aparece no mapa: segue como avulso.
    """
    ids = list(document_ids)
    refs: dict[UUID, list[dict[str, str]]] = defaultdict(list)
    processes = (
        PaymentProcess.objects.filter(Q(invoice_id__in=ids) | Q(boletos__in=ids))
        .exclude(status=PaymentProcess.Status.REJECTED)
        .prefetch_related("boletos")
        .distinct()
    )
    wanted = set(ids)
    for process in processes:
        if process.invoice_id in wanted:
            refs[process.invoice_id].append(
                {"id": str(process.id), "status": process.status, "role": "invoice"}
            )
        for boleto in process.boletos.all():
            if boleto.pk in wanted:
                refs[boleto.pk].append(
                    {"id": str(process.id), "status": process.status, "role": "boleto"}
                )
    return refs
