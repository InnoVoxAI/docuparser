from __future__ import annotations

from rest_framework import serializers

from condominiums.models import Condominium
from condominiums.tax_ids import is_valid_cnpj, normalize_tax_id


class CondominiumSerializer(serializers.ModelSerializer):
    # Aceita o CNPJ formatado (18 caracteres); é gravado sem pontuação.
    cnpj = serializers.CharField(required=False, allow_blank=True, max_length=18)

    class Meta:
        model = Condominium
        fields = [
            "id",
            "name",
            "cnpj",
            "external_id",
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
