from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field

from django.core.management.base import BaseCommand
from docuparse_storage import get_storage

from documents.models import Document

# Prefixo canônico das keys de documento: documents/{tenant}/{document_id}/...
DOCUMENT_KEY_PREFIX = "documents/"


@dataclass
class ReconcileReport:
    # banco → storage: linhas cujo objeto referenciado sumiu do storage
    dangling_refs: list[dict] = field(default_factory=list)
    # storage → banco: objetos cujo document_id não existe mais no banco
    orphan_objects: list[str] = field(default_factory=list)
    deleted_objects: list[str] = field(default_factory=list)
    checked_documents: int = 0
    checked_objects: int = 0
    errors: list[dict] = field(default_factory=list)


class Command(BaseCommand):
    help = (
        "Reconcilia as referências de storage do banco (Document.file_uri / "
        "raw_text_uri) com os objetos no MinIO/disco. Por padrão apenas reporta "
        "(dry-run); use --delete-orphans para remover objetos sem dono."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--direction",
            choices=["both", "db-to-storage", "storage-to-db"],
            default="both",
            help="db-to-storage: acha referências pendentes; storage-to-db: acha objetos órfãos.",
        )
        parser.add_argument(
            "--prefix",
            default=DOCUMENT_KEY_PREFIX,
            help="Prefixo das keys a listar em storage-to-db (default: documents/).",
        )
        parser.add_argument(
            "--delete-orphans",
            action="store_true",
            help="Remove os objetos órfãos encontrados (storage-to-db). Sem isto, só reporta.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Máx. de documentos a checar em db-to-storage (0 = todos).",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emite o relatório em JSON.",
        )

    def handle(self, *args, **options) -> None:
        storage = get_storage()
        report = ReconcileReport()
        direction = options["direction"]

        if direction in ("both", "db-to-storage"):
            self._check_db_to_storage(storage, report, limit=options["limit"])
        if direction in ("both", "storage-to-db"):
            self._check_storage_to_db(
                storage,
                report,
                prefix=options["prefix"],
                delete=options["delete_orphans"],
            )

        self._emit(report, as_json=options["json"])

    # -- banco → storage ---------------------------------------------------

    def _check_db_to_storage(
        self, storage, report: ReconcileReport, *, limit: int
    ) -> None:
        qs = (
            Document.objects.all()
            .only("id", "file_uri", "raw_text_uri")
            .order_by("received_at")
        )
        if limit > 0:
            qs = qs[:limit]
        for doc in qs.iterator():
            report.checked_documents += 1
            for kind, uri in (
                ("file_uri", doc.file_uri),
                ("raw_text_uri", doc.raw_text_uri),
            ):
                if not uri:
                    continue
                try:
                    if not storage.exists(uri):
                        report.dangling_refs.append(
                            {"document_id": str(doc.id), "field": kind, "uri": uri}
                        )
                except Exception as exc:  # noqa: BLE001 - conexão/credencial/backend ausente
                    report.errors.append(
                        {
                            "document_id": str(doc.id),
                            "field": kind,
                            "uri": uri,
                            "error": repr(exc),
                        }
                    )

    # -- storage → banco ---------------------------------------------------

    def _check_storage_to_db(
        self, storage, report: ReconcileReport, *, prefix: str, delete: bool
    ) -> None:
        for key in storage.iter_keys(prefix):
            report.checked_objects += 1
            document_id = self._document_id_from_key(key)
            if document_id is None:
                continue  # key fora do padrão documents/{tenant}/{id}/... — ignora
            if Document.objects.filter(id=document_id).exists():
                continue
            report.orphan_objects.append(key)
            if delete:
                try:
                    storage.delete(key)
                    report.deleted_objects.append(key)
                except Exception as exc:  # noqa: BLE001
                    report.errors.append({"key": key, "error": repr(exc)})

    @staticmethod
    def _document_id_from_key(key: str) -> str | None:
        # documents/{tenant}/{document_id}/original|ocr/raw_text.json
        # Só reconhece keys cujo 3º segmento seja um UUID válido (Document.id),
        # evitando tratar keys fora do padrão como órfãs (e evitando ValidationError
        # ao consultar um UUIDField com string não-UUID).
        parts = key.split("/")
        if len(parts) < 3 or parts[0] != "documents" or not parts[2]:
            return None
        try:
            return str(uuid.UUID(parts[2]))
        except ValueError:
            return None

    # -- saída -------------------------------------------------------------

    def _emit(self, report: ReconcileReport, *, as_json: bool) -> None:
        if as_json:
            self.stdout.write(
                json.dumps(asdict(report), ensure_ascii=False, indent=2, sort_keys=True)
            )
            return

        self.stdout.write(
            f"Documentos checados: {report.checked_documents} | objetos checados: {report.checked_objects}"
        )
        self.stdout.write(
            self.style.WARNING(
                f"Referências pendentes (banco → storage): {len(report.dangling_refs)}"
            )
        )
        for item in report.dangling_refs:
            self.stdout.write(
                f"  {item['document_id']} {item['field']} -> {item['uri']} (objeto ausente)"
            )

        self.stdout.write(
            self.style.WARNING(
                f"Objetos órfãos (storage → banco): {len(report.orphan_objects)}"
            )
        )
        for key in report.orphan_objects:
            marker = "removido" if key in report.deleted_objects else "sem dono"
            self.stdout.write(f"  {key} ({marker})")

        if report.errors:
            self.stdout.write(self.style.ERROR(f"Erros: {len(report.errors)}"))
            for err in report.errors:
                self.stdout.write(f"  {err}")

        if not report.dangling_refs and not report.orphan_objects and not report.errors:
            self.stdout.write(
                self.style.SUCCESS("Consistente: banco e storage reconciliados.")
            )
