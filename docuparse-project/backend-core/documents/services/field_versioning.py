"""Versionamento de campos extraídos.

Cada salvamento (manual ou automático) cria uma nova ``ExtractionFieldVersion``
imutável e a torna a versão ativa do documento, mantendo o ``ExtractionResult``
(ponteiro OneToOne) sincronizado com a versão ativa.

Feature: docs/specs/007-extracted-field-versioning/
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from documents.models import Document, ExtractionFieldVersion


class VersionConflictError(Exception):
    """Edições baseadas numa versão que não é mais a ativa (FR-024)."""

    def __init__(self, active_version_number: int | None) -> None:
        self.active_version_number = active_version_number
        super().__init__("A versão base não é mais a versão ativa.")


class EmptyFieldListError(Exception):
    """Tentativa de persistir uma lista de campos vazia."""


class NoChangesError(Exception):
    """Salvamento manual sem alterações em relação à versão ativa."""


def get_active_version(document: Document) -> ExtractionFieldVersion | None:
    return document.field_versions.filter(is_active=True).first()


def _next_version_number(document: Document) -> int:
    last = document.field_versions.order_by("-version_number").first()
    return (last.version_number if last else 0) + 1


def _parse_entry(raw: Any) -> tuple[str, float | None]:
    """Normaliza um campo (escalar ou ``{value, confidence}``) em (valor, confiança)."""
    if isinstance(raw, dict) and "value" in raw:
        value = raw.get("value")
        confidence = raw.get("confidence")
        return (
            "" if value is None else str(value),
            confidence if isinstance(confidence, (int, float)) else None,
        )
    if raw is None:
        return ("", None)
    return (str(raw), None)


def _aggregate_confidence(fields: dict[str, Any]) -> float:
    confs = [
        f["confidence"]
        for f in fields.values()
        if isinstance(f, dict) and isinstance(f.get("confidence"), (int, float))
    ]
    return round(sum(confs) / len(confs), 4) if confs else 0.0


def _sync_extraction_result(document: Document, version: ExtractionFieldVersion) -> None:
    result = getattr(document, "extraction_result", None)
    if result is None:
        return
    result.fields = version.fields
    result.confidence = version.confidence
    result.save(update_fields=["fields", "confidence", "updated_at"])


@transaction.atomic
def create_version(
    document: Document,
    *,
    fields: dict[str, Any],
    source_type: str,
    created_by: Any = None,
    confidence: float | None = None,
) -> ExtractionFieldVersion:
    """Cria uma nova versão ativa, desativando a anterior e sincronizando o
    ``ExtractionResult``. Não sobrescreve nenhuma versão existente (FR-013/FR-016).
    """
    active = (
        document.field_versions.select_for_update().filter(is_active=True).first()
    )
    version_number = _next_version_number(document)
    if confidence is None:
        confidence = _aggregate_confidence(fields)
    if active is not None:
        active.is_active = False
        active.save(update_fields=["is_active", "updated_at"])
    version = ExtractionFieldVersion.objects.create(
        document=document,
        version_number=version_number,
        source_type=source_type,
        fields=fields,
        confidence=confidence,
        previous_version=active,
        created_by=created_by,
        is_active=True,
    )
    _sync_extraction_result(document, version)
    return version


def initial_or_reprocess_source(document: Document) -> str:
    """Tipo de origem para extração automática: inicial se não houver versão."""
    if document.field_versions.exists():
        return ExtractionFieldVersion.SourceType.REPROCESSING
    return ExtractionFieldVersion.SourceType.INITIAL_EXTRACTION


def _build_manual_snapshot(
    active: ExtractionFieldVersion | None, incoming: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Monta o snapshot ``{nome: {value, confidence}}`` aplicando FR-025/FR-027:
    campos alterados ou adicionados recebem confiança 1.0; inalterados mantêm a sua.
    """
    base: dict[str, tuple[str, float | None]] = {}
    if active is not None:
        for name, raw in (active.fields or {}).items():
            base[name] = _parse_entry(raw)

    snapshot: dict[str, dict[str, Any]] = {}
    for item in incoming:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        value = "" if item.get("value") is None else str(item.get("value"))
        prev = base.get(name)
        if prev is not None and prev[0] == value:
            confidence = prev[1]  # inalterado: mantém confiança (pode ser None)
        else:
            confidence = 1.0  # alterado ou novo (FR-025/FR-027)
        snapshot[name] = {"value": value, "confidence": confidence}
    return snapshot


def _has_changes(
    active: ExtractionFieldVersion | None, snapshot: dict[str, dict[str, Any]]
) -> bool:
    new_values = {name: field["value"] for name, field in snapshot.items()}
    if active is None:
        return bool(new_values)
    base_values = {
        name: _parse_entry(raw)[0] for name, raw in (active.fields or {}).items()
    }
    return base_values != new_values


def save_manual_edit(
    document: Document,
    *,
    incoming_fields: list[dict[str, Any]],
    base_version_number: int | None,
    created_by: Any = None,
) -> ExtractionFieldVersion:
    """Salva edições/remoções/adições como nova versão ``MANUAL_EDIT`` (US1/US2).

    Levanta ``VersionConflictError`` se ``base_version_number`` não for a versão
    ativa atual (FR-024), ``EmptyFieldListError`` para lista vazia e
    ``NoChangesError`` quando não há alterações.
    """
    active = get_active_version(document)
    active_number = active.version_number if active is not None else None
    if base_version_number != active_number:
        raise VersionConflictError(active_number)

    snapshot = _build_manual_snapshot(active, incoming_fields)
    if not snapshot:
        raise EmptyFieldListError()
    if not _has_changes(active, snapshot):
        raise NoChangesError()

    return create_version(
        document,
        fields=snapshot,
        source_type=ExtractionFieldVersion.SourceType.MANUAL_EDIT,
        created_by=created_by,
    )
