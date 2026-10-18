from __future__ import annotations

from typing import Any

from accounting.models import ChartOfAccounts
from rest_framework import serializers

from condominiums.models import Condominium
from condominiums.tax_ids import is_valid_cnpj, normalize_tax_id
from condominiums.text import normalize_text


class CondominiumSerializer(serializers.ModelSerializer):
    # Aceita o CNPJ formatado (18 caracteres); é gravado sem pontuação.
    cnpj = serializers.CharField(required=False, allow_blank=True, max_length=18)
    aliases = serializers.ListField(
        child=serializers.CharField(max_length=255, allow_blank=True),
        required=False,
    )
    chart_of_accounts_id = serializers.PrimaryKeyRelatedField(
        queryset=ChartOfAccounts.objects.all(),
        source="chart_of_accounts",
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Condominium
        fields = [
            "id",
            "name",
            "cnpj",
            "external_source",
            "external_id",
            "chart_of_accounts_id",
            "aliases",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_cnpj(self, value: str) -> str:
        cnpj = normalize_tax_id(value)
        if not cnpj:
            return ""
        if not is_valid_cnpj(cnpj):
            raise serializers.ValidationError("CNPJ inválido.")
        duplicates = Condominium.objects.filter(cnpj=cnpj)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("Já existe um condomínio com este CNPJ.")
        return cnpj

    def validate_aliases(self, value: list[str]) -> list[str]:
        aliases: dict[str, str] = {}
        for alias in value:
            key = normalize_text(alias)
            if key:
                aliases.setdefault(key, alias.strip())

        taken = {}
        for other in Condominium.objects.exclude(pk=getattr(self.instance, "pk", None)):
            for name in (other.name, *other.aliases):
                taken[normalize_text(name)] = other.name
        for key in aliases:
            if key in taken:
                raise serializers.ValidationError(
                    f"'{aliases[key]}' já identifica o condomínio '{taken[key]}'."
                )
        return list(aliases.values())

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        source = attrs.get(
            "external_source", getattr(self.instance, "external_source", "")
        )
        external_id = attrs.get(
            "external_id", getattr(self.instance, "external_id", "")
        )
        if external_id:
            clash = Condominium.objects.filter(
                external_source=source, external_id=external_id
            )
            if self.instance is not None:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"external_id": "Já existe um condomínio com este id nesta origem."}
                )

        # As regras de fornecedor apontam para contas do plano atual.
        if (
            self.instance is not None
            and "chart_of_accounts" in attrs
            and attrs["chart_of_accounts"] != self.instance.chart_of_accounts
            and self.instance.supplier_rules.exists()
        ):
            raise serializers.ValidationError(
                {
                    "chart_of_accounts_id": "Remova as regras de fornecedor antes de trocar o plano de contas."
                }
            )
        return attrs
