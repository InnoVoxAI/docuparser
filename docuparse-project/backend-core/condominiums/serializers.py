from __future__ import annotations

import re

from rest_framework import serializers

from condominiums.models import Condominium

_CNPJ_FORMAT = re.compile(r"[0-9A-Z]{12}[0-9]{2}")
_CNPJ_WEIGHTS = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _cnpj_check_digit(base: str) -> str:
    weights = _CNPJ_WEIGHTS[-len(base) :]
    total = sum((ord(char) - 48) * weight for char, weight in zip(base, weights))
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


def is_valid_cnpj(cnpj: str) -> bool:
    """Valida formato e dígitos verificadores, inclusive do CNPJ alfanumérico."""
    if not _CNPJ_FORMAT.fullmatch(cnpj) or len(set(cnpj)) == 1:
        return False
    first = _cnpj_check_digit(cnpj[:12])
    return cnpj[12:] == first + _cnpj_check_digit(cnpj[:12] + first)


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
        cnpj = re.sub(r"[\s./-]", "", value).upper()
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
