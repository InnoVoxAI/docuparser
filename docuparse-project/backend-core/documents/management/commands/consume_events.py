from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from docuparse_events import event_bus_from_env

from documents.services.event_stream_worker import CoreEventStreamWorker


class Command(BaseCommand):
    help = "Consume DocuParse event streams and update backend-core state."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process available events once and exit.",
        )
        parser.add_argument(
            "--from-beginning",
            action="store_true",
            help="Start from the beginning of each stream instead of only new events.",
        )
        parser.add_argument(
            "--poll-seconds",
            type=float,
            default=1.0,
            help="Seconds to wait between empty polling cycles.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=25,
            help="Maximum events read per stream on each polling cycle.",
        )

    def handle(self, *args, **options) -> None:
        worker = CoreEventStreamWorker(
            event_bus=event_bus_from_env(settings.DOCUPARSE_LOCAL_EVENT_DIR),
            poll_seconds=options["poll_seconds"],
            batch_size=options["batch_size"],
            start_at_latest=not options["from_beginning"],
        )
        if options["once"]:
            processed_count = worker.run_once()
            self.stdout.write(f"Processed {processed_count} event(s).")
            return
        worker.run_forever()
