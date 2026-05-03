from __future__ import annotations

import json

from django.conf import settings
from django.core.management.base import BaseCommand

from docuparse_events import event_bus_from_env
from documents.services.dlq_inspector import DEFAULT_DLQ_STREAMS, inspect_dlq_streams


class Command(BaseCommand):
    help = "Inspect DocuParse dead-letter queues."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--stream",
            action="append",
            dest="streams",
            help="DLQ stream to inspect. Can be passed multiple times. Defaults to known DLQ streams.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Maximum entries per DLQ stream.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit machine-readable JSON.",
        )
        parser.add_argument(
            "--summary",
            action="store_true",
            help="Only show counts per DLQ stream.",
        )

    def handle(self, *args, **options) -> None:
        event_bus = event_bus_from_env(settings.DOCUPARSE_LOCAL_EVENT_DIR)
        streams = options["streams"] or DEFAULT_DLQ_STREAMS
        limit = options["limit"]
        report = inspect_dlq_streams(event_bus, streams=streams, limit=limit)

        if options["json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            return

        for item in report:
            self.stdout.write(f"{item['stream']}: {item['count']}")
            if options["summary"]:
                continue
            for entry in item["entries"]:
                self.stdout.write(
                    "  "
                    f"{entry['id']} "
                    f"event_type={entry['event_type'] or '-'} "
                    f"event_id={entry['event_id'] or '-'} "
                    f"source={entry['source'] or '-'} "
                    f"error_type={entry['error_type'] or '-'} "
                    f"error={entry['error'] or '-'}"
                )
