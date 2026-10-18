from __future__ import annotations

from rest_framework import serializers

from erp_import.models import ImportBatch, ImportProposal


def _username(user) -> str | None:
    return user.get_username() if user else None


class ImportBatchSerializer(serializers.ModelSerializer):
    started_by = serializers.SerializerMethodField()

    class Meta:
        model = ImportBatch
        fields = [
            "id",
            "source",
            "status",
            "error_message",
            "started_by",
            "created_at",
            "finished_at",
        ]

    def get_started_by(self, obj: ImportBatch) -> str | None:
        return _username(obj.started_by)


class ImportProposalSerializer(serializers.ModelSerializer):
    batch_id = serializers.UUIDField(read_only=True)
    decided_by = serializers.SerializerMethodField()

    class Meta:
        model = ImportProposal
        fields = [
            "id",
            "batch_id",
            "entity_type",
            "external_id",
            "action",
            "data",
            "diff",
            "warnings",
            "status",
            "resolution",
            "decided_by",
            "decided_at",
            "created_at",
        ]

    def get_decided_by(self, obj: ImportProposal) -> str | None:
        return _username(obj.decided_by)


class ResolveSerializer(serializers.Serializer):
    resolution = serializers.DictField()


class BulkDecisionSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False, max_length=1000
    )
