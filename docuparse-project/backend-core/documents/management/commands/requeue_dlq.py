from __future__ import annotations

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from docuparse_events import event_bus_from_env
from documents.services.dlq_inspector import requeue_dlq_entry


class Command(BaseCommand):
    help = "Requeue a reviewed DocuParse DLQ entry."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--stream", required=True, help="DLQ stream, for example ocr.completed.dlq.")
        parser.add_argument("--id", required=True, dest="entry_id", help="DLQ entry id.")
        parser.add_argument("--target-stream", help="Target stream. Defaults to the original stream stored in the DLQ entry.")
        parser.add_argument("--note", default="", help="Operational note stored in the requeue audit stream.")
        parser.add_argument("--requested-by", default="cli", help="Operator identifier stored in the audit event.")
        parser.add_argument("--limit", type=int, default=500, help="Maximum DLQ entries to scan when locating the id.")
        parser.add_argument("--execute", action="store_true", help="Publish the original payload back to the target stream.")
        parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    def handle(self, *args, **options) -> None:
        event_bus = event_bus_from_env(settings.DOCUPARSE_LOCAL_EVENT_DIR)
        try:
            result = requeue_dlq_entry(
                event_bus,
                stream=options["stream"],
                entry_id=options["entry_id"],
                target_stream=options["target_stream"],
                note=options["note"],
                requested_by=options["requested_by"],
                execute=options["execute"],
                limit=options["limit"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if options["json"]:
            self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return

        action = "REQUEUED" if result["execute"] else "DRY-RUN"
        self.stdout.write(
            f"{action} {result['dlq_stream']}#{result['dlq_entry_id']} -> {result['target_stream']} "
            f"event_type={result['event_type'] or '-'} event_id={result['event_id'] or '-'}"
        )
        if not result["execute"]:
            self.stdout.write("Use --execute to publish the original payload back to the target stream.")
        elif result["requeued_event_stream_id"]:
            self.stdout.write(f"Published as stream id {result['requeued_event_stream_id']}.")
