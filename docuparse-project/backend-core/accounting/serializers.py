from __future__ import annotations

from typing import Any

from condominiums.models import Condominium
from condominiums.tax_ids import is_valid_tax_id, normalize_tax_id
from rest_framework import serializers

from accounting.models import DocumentClassification, LedgerAccount, SupplierRule


def _is_self_or_descendant(candidate: LedgerAccount, account: LedgerAccount) -> bool:
    node: LedgerAccount | None = candidate
    while node is not None:
        if node.pk == account.pk:
            return True
        node = node.parent
    return False


class LedgerAccountSerializer(serializers.ModelSerializer):
    """Espera `context["condominium"]` ao validar escrita."""

    condominium_id = serializers.UUIDField(read_only=True)
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=LedgerAccount.objects.all(),
        source="parent",
        allow_null=True,
        required=False,
    )

    class Meta:
        model = LedgerAccount
        fields = [
            "id",
            "condominium_id",
            "parent_id",
            "code",
            "name",
            "nature",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        condominium = self.context["condominium"]

        code = attrs.get("code")
        if code is not None:
            clash = LedgerAccount.objects.filter(condominium=condominium, code=code)
            if self.instance is not None:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"code": "Já existe uma conta com este código neste condomínio."}
                )

        nature = attrs.get("nature")
        if nature:
            clash = LedgerAccount.objects.filter(condominium=condominium, nature=nature)
            if self.instance is not None:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"nature": "Outra conta deste condomínio já recebe esta natureza."}
                )

        parent = attrs.get("parent")
        if parent is not None:
            if parent.condominium_id != condominium.id:
                raise serializers.ValidationError(
                    {"parent_id": "A conta pai precisa ser do mesmo condomínio."}
                )
            if self.instance is not None and _is_self_or_descendant(
                parent, self.instance
            ):
                raise serializers.ValidationError(
                    {"parent_id": "Uma conta não pode ficar abaixo dela mesma."}
                )
        return attrs


class SupplierRuleSerializer(serializers.ModelSerializer):
    """Espera `context["condominium"]` ao validar escrita."""

    condominium_id = serializers.UUIDField(read_only=True)
    # Aceita CNPJ ou CPF formatado; é gravado sem pontuação.
    supplier_tax_id = serializers.CharField(max_length=18)
    ledger_account_id = serializers.PrimaryKeyRelatedField(
        queryset=LedgerAccount.objects.all(), source="ledger_account"
    )

    class Meta:
        model = SupplierRule
        fields = [
            "id",
            "condominium_id",
            "supplier_tax_id",
            "keyword",
            "ledger_account_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_supplier_tax_id(self, value: str) -> str:
        tax_id = normalize_tax_id(value)
        if not is_valid_tax_id(tax_id):
            raise serializers.ValidationError("CNPJ ou CPF inválido.")
        return tax_id

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        condominium = self.context["condominium"]

        account = attrs.get("ledger_account")
        if account is not None and account.condominium_id != condominium.id:
            raise serializers.ValidationError(
                {"ledger_account_id": "A conta precisa ser do mesmo condomínio."}
            )

        tax_id = attrs.get(
            "supplier_tax_id", getattr(self.instance, "supplier_tax_id", "")
        )
        keyword = attrs.get("keyword", getattr(self.instance, "keyword", ""))
        clash = SupplierRule.objects.filter(
            condominium=condominium, supplier_tax_id=tax_id, keyword=keyword
        )
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                {"keyword": "Já existe uma regra para este fornecedor com este trecho."}
            )
        return attrs


class LedgerAccountRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerAccount
        fields = ["id", "code", "name"]


class DocumentClassificationSerializer(serializers.ModelSerializer):
    document_id = serializers.UUIDField(read_only=True)
    ledger_account_id = serializers.UUIDField(read_only=True)
    ledger_account = LedgerAccountRefSerializer(read_only=True)
    classified_by = serializers.SerializerMethodField()

    class Meta:
        model = DocumentClassification
        fields = [
            "document_id",
            "ledger_account_id",
            "ledger_account",
            "origin",
            "rule_id",
            "reason",
            "classified_by",
            "updated_at",
        ]

    def get_classified_by(self, obj: DocumentClassification) -> str | None:
        return obj.classified_by.get_username() if obj.classified_by else None


class ManualClassificationSerializer(serializers.Serializer):
    """Espera `context["document"]`: a conta precisa ser do condomínio dele."""

    ledger_account_id = serializers.PrimaryKeyRelatedField(
        queryset=LedgerAccount.objects.filter(is_active=True),
        source="ledger_account",
        error_messages={"does_not_exist": "Conta não encontrada ou inativa."},
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        document = self.context["document"]
        if document.condominium_id is None:
            raise serializers.ValidationError(
                {
                    "ledger_account_id": "Defina o condomínio do documento antes de escolher a conta."
                }
            )
        if attrs["ledger_account"].condominium_id != document.condominium_id:
            raise serializers.ValidationError(
                {"ledger_account_id": "A conta precisa ser do condomínio do documento."}
            )
        return attrs


class ManualCondominiumSerializer(serializers.Serializer):
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.filter(is_active=True),
        source="condominium",
        error_messages={"does_not_exist": "Condomínio não encontrado ou inativo."},
    )
