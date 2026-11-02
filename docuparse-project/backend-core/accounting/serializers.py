from __future__ import annotations

from typing import Any

from condominiums.models import Condominium
from condominiums.tax_ids import is_valid_tax_id, normalize_tax_id
from condominiums.text import normalize_text
from rest_framework import serializers

from accounting.models import (
    ChartOfAccounts,
    DocumentClassification,
    LedgerAccount,
    SupplierRule,
)


def _is_self_or_descendant(candidate: LedgerAccount, account: LedgerAccount) -> bool:
    node: LedgerAccount | None = candidate
    while node is not None:
        if node.pk == account.pk:
            return True
        node = node.parent
    return False


class ChartOfAccountsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartOfAccounts
        fields = [
            "id",
            "name",
            "external_source",
            "external_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        source = attrs.get(
            "external_source", getattr(self.instance, "external_source", "")
        )
        external_id = attrs.get(
            "external_id", getattr(self.instance, "external_id", "")
        )
        if external_id:
            clash = ChartOfAccounts.objects.filter(
                external_source=source, external_id=external_id
            )
            if self.instance is not None:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {
                        "external_id": "Já existe um plano de contas com este id nesta origem."
                    }
                )
        return attrs


class LedgerAccountSerializer(serializers.ModelSerializer):
    """Espera `context["chart"]` ao validar escrita."""

    chart_id = serializers.UUIDField(read_only=True)
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
            "chart_id",
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
        chart = self.context["chart"]

        code = attrs.get("code")
        if code is not None:
            clash = LedgerAccount.objects.filter(chart=chart, code=code)
            if self.instance is not None:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"code": "Já existe uma conta com este código neste plano."}
                )

        nature = attrs.get("nature")
        if nature:
            clash = LedgerAccount.objects.filter(chart=chart, nature=nature)
            if self.instance is not None:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"nature": "Outra conta deste plano já recebe esta natureza."}
                )

        parent = attrs.get("parent")
        if parent is not None:
            if parent.chart_id != chart.id:
                raise serializers.ValidationError(
                    {"parent_id": "A conta pai precisa ser do mesmo plano."}
                )
            if self.instance is not None and _is_self_or_descendant(
                parent, self.instance
            ):
                raise serializers.ValidationError(
                    {"parent_id": "Uma conta não pode ficar abaixo dela mesma."}
                )
        return attrs


class SupplierRuleSerializer(serializers.ModelSerializer):
    """Espera `context["chart"]` e, para regra só de um condomínio, `context["condominium"]`."""

    chart_id = serializers.UUIDField(read_only=True)
    condominium_id = serializers.UUIDField(read_only=True)
    # Aceita CNPJ ou CPF formatado; é gravado sem pontuação. Vazio: regra por nome
    # (o nome do fornecedor vai em `keyword`).
    supplier_tax_id = serializers.CharField(
        max_length=18, required=False, allow_blank=True
    )
    ledger_account_id = serializers.PrimaryKeyRelatedField(
        queryset=LedgerAccount.objects.all(), source="ledger_account"
    )
    ledger_account = serializers.SerializerMethodField()
    # A regra pré-preenche a conta dos documentos novos neste momento.
    prefills = serializers.SerializerMethodField()

    class Meta:
        model = SupplierRule
        fields = [
            "id",
            "chart_id",
            "condominium_id",
            "supplier_tax_id",
            "keyword",
            "ledger_account_id",
            "ledger_account",
            "is_active",
            "prefills",
            "origin",
            "evidence_count",
            "evidence_total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "origin",
            "evidence_count",
            "evidence_total",
            "created_at",
            "updated_at",
        ]

    def get_ledger_account(self, obj: SupplierRule) -> dict[str, str]:
        account = obj.ledger_account
        return {"id": str(account.id), "code": account.code, "name": account.name}

    def get_prefills(self, obj: SupplierRule) -> bool:
        return obj.is_active and obj.ledger_account.is_active and obj.is_confident

    def validate_supplier_tax_id(self, value: str) -> str:
        tax_id = normalize_tax_id(value)
        if tax_id and not is_valid_tax_id(tax_id):
            raise serializers.ValidationError("CNPJ ou CPF inválido.")
        return tax_id

    def update(
        self, instance: SupplierRule, validated_data: dict[str, Any]
    ) -> SupplierRule:
        # Mexer na regra é decisão do analista: a atualização do histórico não a desfaz.
        validated_data["origin"] = SupplierRule.Origin.MANUAL
        return super().update(instance, validated_data)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        chart = self.context["chart"]
        condominium = self.context.get("condominium")

        account = attrs.get("ledger_account")
        if account is not None and account.chart_id != chart.id:
            raise serializers.ValidationError(
                {
                    "ledger_account_id": "A conta precisa ser do plano de contas da regra."
                }
            )

        tax_id = attrs.get(
            "supplier_tax_id", getattr(self.instance, "supplier_tax_id", "")
        )
        keyword = attrs.get("keyword", getattr(self.instance, "keyword", ""))
        if not tax_id:
            name = normalize_text(keyword)
            if (
                not SupplierRule.MIN_NAME_LENGTH
                <= len(name)
                <= SupplierRule.MAX_NAME_LENGTH
            ):
                raise serializers.ValidationError(
                    {
                        "keyword": f"Sem CNPJ ou CPF, informe o nome do fornecedor ({SupplierRule.MIN_NAME_LENGTH} a {SupplierRule.MAX_NAME_LENGTH} caracteres)."
                    }
                )
        clash = SupplierRule.objects.filter(
            chart=chart,
            condominium=condominium,
            supplier_tax_id=tax_id,
            keyword=keyword,
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
    """Espera `context["document"]`: a conta precisa ser do plano do condomínio dele."""

    ledger_account_id = serializers.PrimaryKeyRelatedField(
        queryset=LedgerAccount.objects.filter(is_active=True),
        source="ledger_account",
        error_messages={"does_not_exist": "Conta não encontrada ou inativa."},
    )
    # "Usar sempre esta conta para este fornecedor": cria uma regra que vale sempre.
    remember = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        document = self.context["document"]
        if document.condominium_id is None:
            raise serializers.ValidationError(
                {
                    "ledger_account_id": "Defina o condomínio do documento antes de escolher a conta."
                }
            )
        chart_id = document.condominium.chart_of_accounts_id
        if chart_id is None:
            raise serializers.ValidationError(
                {
                    "ledger_account_id": "O condomínio do documento não tem plano de contas."
                }
            )
        if attrs["ledger_account"].chart_id != chart_id:
            raise serializers.ValidationError(
                {
                    "ledger_account_id": "A conta precisa ser do plano de contas do condomínio do documento."
                }
            )
        return attrs


class ManualCondominiumSerializer(serializers.Serializer):
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.filter(is_active=True),
        source="condominium",
        error_messages={"does_not_exist": "Condomínio não encontrado ou inativo."},
    )
