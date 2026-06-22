"""Unit tests for the field versioning service (T008)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from documents.models import Document, ExtractionFieldVersion, ExtractionResult, Tenant
from documents.services import field_versioning as fv


class FieldVersioningServiceTests(TestCase):
    def setUp(self) -> None:
        self.tenant = Tenant.objects.create(slug="t-fv", name="Tenant FV")
        self.user = get_user_model().objects.create_user(username="editor", password="x")
        self.document = Document.objects.create(
            tenant=self.tenant,
            status=Document.Status.EXTRACTION_COMPLETED,
            channel="manual",
            file_uri="local://doc",
            content_type="application/pdf",
            size_bytes=10,
        )
        self.extraction = ExtractionResult.objects.create(
            document=self.document,
            schema_id="s",
            schema_version="v1",
            fields={"valor": {"value": "100", "confidence": 0.8}},
            confidence=0.8,
        )
        self.v1 = fv.create_version(
            self.document,
            fields={"valor": {"value": "100", "confidence": 0.8}},
            source_type=ExtractionFieldVersion.SourceType.INITIAL_EXTRACTION,
        )

    def test_first_version_is_active_and_numbered_one(self) -> None:
        assert self.v1.version_number == 1
        assert self.v1.is_active is True
        assert self.v1.previous_version is None
        assert fv.get_active_version(self.document) == self.v1

    def test_new_version_deactivates_previous_and_links_back(self) -> None:
        v2 = fv.save_manual_edit(
            self.document,
            incoming_fields=[{"name": "valor", "value": "200"}],
            base_version_number=1,
            created_by=self.user,
        )
        self.v1.refresh_from_db()
        assert v2.version_number == 2
        assert v2.is_active is True
        assert self.v1.is_active is False
        assert v2.previous_version_id == self.v1.id
        # exactly one active version
        assert ExtractionFieldVersion.objects.filter(document=self.document, is_active=True).count() == 1

    def test_changed_field_gets_confidence_one(self) -> None:
        v2 = fv.save_manual_edit(
            self.document,
            incoming_fields=[{"name": "valor", "value": "200"}],
            base_version_number=1,
        )
        assert v2.fields["valor"]["confidence"] == 1.0

    def test_unchanged_field_keeps_confidence(self) -> None:
        v2 = fv.save_manual_edit(
            self.document,
            incoming_fields=[
                {"name": "valor", "value": "100"},  # inalterado
                {"name": "novo", "value": "x"},  # adicionado força nova versão
            ],
            base_version_number=1,
        )
        assert v2.fields["valor"]["confidence"] == 0.8

    def test_added_field_gets_confidence_one(self) -> None:
        v2 = fv.save_manual_edit(
            self.document,
            incoming_fields=[
                {"name": "valor", "value": "100"},
                {"name": "fornecedor", "value": "ACME"},
            ],
            base_version_number=1,
        )
        assert v2.fields["fornecedor"]["confidence"] == 1.0

    def test_version_conflict_raises_and_creates_no_version(self) -> None:
        # Outra versão torna a base 1 obsoleta.
        fv.save_manual_edit(
            self.document,
            incoming_fields=[{"name": "valor", "value": "200"}],
            base_version_number=1,
        )
        with self.assertRaises(fv.VersionConflictError) as ctx:
            fv.save_manual_edit(
                self.document,
                incoming_fields=[{"name": "valor", "value": "300"}],
                base_version_number=1,  # obsoleta
            )
        assert ctx.exception.active_version_number == 2
        assert ExtractionFieldVersion.objects.filter(document=self.document).count() == 2

    def test_empty_field_list_raises(self) -> None:
        with self.assertRaises(fv.EmptyFieldListError):
            fv.save_manual_edit(
                self.document,
                incoming_fields=[],
                base_version_number=1,
            )
        assert ExtractionFieldVersion.objects.filter(document=self.document).count() == 1

    def test_no_changes_raises(self) -> None:
        with self.assertRaises(fv.NoChangesError):
            fv.save_manual_edit(
                self.document,
                incoming_fields=[{"name": "valor", "value": "100"}],
                base_version_number=1,
            )

    def test_removed_field_excluded_but_previous_preserved(self) -> None:
        # v1 tem valor + extra; remover extra na próxima versão.
        v_with_extra = fv.save_manual_edit(
            self.document,
            incoming_fields=[
                {"name": "valor", "value": "100"},
                {"name": "extra", "value": "remover"},
            ],
            base_version_number=1,
        )
        v_without = fv.save_manual_edit(
            self.document,
            incoming_fields=[{"name": "valor", "value": "100"}],
            base_version_number=v_with_extra.version_number,
        )
        assert "extra" not in v_without.fields
        assert "extra" in v_with_extra.fields  # versão anterior preservada (FR-013)

    def test_create_version_syncs_extraction_result(self) -> None:
        fv.save_manual_edit(
            self.document,
            incoming_fields=[{"name": "valor", "value": "999"}],
            base_version_number=1,
        )
        self.extraction.refresh_from_db()
        assert self.extraction.fields["valor"]["value"] == "999"

    def test_no_version_is_overwritten(self) -> None:
        original_id = self.v1.id
        fv.save_manual_edit(
            self.document,
            incoming_fields=[{"name": "valor", "value": "200"}],
            base_version_number=1,
        )
        # v1 ainda existe, imutável em fields
        self.v1.refresh_from_db()
        assert self.v1.id == original_id
        assert self.v1.fields == {"valor": {"value": "100", "confidence": 0.8}}
