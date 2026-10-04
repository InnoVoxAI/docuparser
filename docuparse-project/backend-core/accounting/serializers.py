from __future__ import annotations

from typing import Any

from rest_framework import serializers

from accounting.models import LedgerAccount


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
