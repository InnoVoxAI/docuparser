from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from docuparse_storage import LocalStorage
from docuparse_storage.factory import _build_s3_from_env
from docuparse_storage.migration import migrate_documents

from documents.models import Document


class Command(BaseCommand):
    help = (
        "Migra os artefatos de documentos de local:// para s3:// (feature 011): "
        "lê os bytes do disco local, grava no S3/MinIO na mesma key e atualiza a "
        "URI no banco. Idempotente e retomável — itens não migrados seguem legíveis."
    )

    def add_arguments(self, parser) -> None:
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--dry-run", action="store_true", help="apenas relata, não grava")
        group.add_argument("--apply", action="store_true", help="executa a migração")

    def handle(self, *args, **options) -> None:
        dry_run = options["dry_run"]
        local = LocalStorage(settings.DOCUPARSE_LOCAL_STORAGE_DIR)
        s3 = _build_s3_from_env()  # falha explícita se S3/MinIO não estiver configurado

        stats = migrate_documents(
            Document.objects.all().iterator(), local, s3, dry_run=dry_run
        )

        mode = "DRY-RUN (nada gravado)" if dry_run else "APLICADO"
        self.stdout.write(f"Migração local:// → s3:// [{mode}]")
        self.stdout.write(
            f"  escaneados: {stats.scanned} | migrados: {stats.migrated} | "
            f"pulados (já s3/vazios): {stats.skipped} | "
            f"sem arquivo no disco (ignorados): {len(stats.missing)}"
        )

        if stats.missing:
            self.stdout.write(
                self.style.WARNING(
                    "  Ignorados (binário já perdido no disco, nada a migrar — "
                    "abrir o arquivo desses documentos dará 404):"
                )
            )
            for item in stats.missing:
                self.stdout.write(f"    - {item}")

        # Erros inesperados (ex.: S3 indisponível) — estes falham a execução.
        if stats.errors:
            for err in stats.errors:
                self.stdout.write(self.style.ERROR(f"  erro: {err}"))
            raise CommandError(f"Migração terminou com {len(stats.errors)} erro(s) inesperado(s).")

        if not dry_run:
            self.stdout.write(self.style.SUCCESS("Migração concluída."))
