"""Processa a fila durável (`ProcessingJob`).

    python manage.py run_worker [--concurrency 2] [--poll-interval 2]
                                [--steps ocr,extraction,erp_dispatch]

SIGTERM/SIGINT param os claims e esperam os jobs em curso até
`DOCUPARSE_WORKER_SHUTDOWN_GRACE` segundos (padrão 330: o OCR tem timeout de
300 s). Um segundo sinal, mandado mais de 2 s depois do primeiro, sai na
hora. Ver `jobqueue/worker.py`.
"""

from __future__ import annotations

import logging
import os
import signal
import time

from django.core.management.base import BaseCommand, CommandError

from jobqueue.worker import ALL_STEPS, DEFAULT_SHUTDOWN_GRACE, Worker

logger = logging.getLogger(__name__)

SHUTDOWN_GRACE_ENV = "DOCUPARSE_WORKER_SHUTDOWN_GRACE"
# Sinais repetidos dentro desta janela são o mesmo sinal repassado pelo uv.
DUPLICATE_SIGNAL_WINDOW = 2.0


def _shutdown_grace() -> float:
    raw = os.environ.get(SHUTDOWN_GRACE_ENV, "").strip()
    if not raw:
        return DEFAULT_SHUTDOWN_GRACE
    try:
        value = float(raw)
    except ValueError:
        raise CommandError(f"{SHUTDOWN_GRACE_ENV} inválido: {raw!r}") from None
    if value < 0:
        raise CommandError(f"{SHUTDOWN_GRACE_ENV} não pode ser negativo: {raw!r}")
    return value


class Command(BaseCommand):
    help = "Processa os jobs da fila durável (ocr, extraction, erp_dispatch)."

    def add_arguments(self, parser):
        parser.add_argument("--concurrency", type=int, default=2)
        parser.add_argument("--poll-interval", type=float, default=2.0)
        parser.add_argument(
            "--steps",
            default=",".join(ALL_STEPS),
            help=f"Etapas separadas por vírgula (padrão: {','.join(ALL_STEPS)}).",
        )

    def handle(self, *args, **options):
        steps = tuple(s.strip() for s in options["steps"].split(",") if s.strip())
        unknown = sorted(set(steps) - set(ALL_STEPS))
        if unknown or not steps:
            raise CommandError(
                f"--steps inválido: {unknown or options['steps']!r}. "
                f"Use {', '.join(ALL_STEPS)}."
            )
        if options["concurrency"] < 1:
            raise CommandError("--concurrency deve ser >= 1")
        if options["poll_interval"] <= 0:
            raise CommandError("--poll-interval deve ser > 0")

        worker = Worker(
            concurrency=options["concurrency"],
            poll_interval=options["poll_interval"],
            steps=steps,
            shutdown_grace=_shutdown_grace(),
        )

        first_signal_at: list[float] = []

        def _on_signal(signum, _frame):
            now = time.monotonic()
            if not first_signal_at:
                first_signal_at.append(now)
                logger.info("jobqueue_worker_signal | signal=%s", signum)
                worker.stop()
                return
            # O `uv run` repassa o sinal ao python: um sinal mandado ao grupo de
            # processos (Ctrl+C no terminal, pkill) chega duas vezes quase
            # juntas. Só um segundo sinal mandado depois de propósito força a
            # saída sem esperar o prazo.
            if now - first_signal_at[0] < DUPLICATE_SIGNAL_WINDOW:
                return
            logger.warning("jobqueue_worker_forced_exit | signal=%s", signum)
            os._exit(1)

        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT, _on_signal)
        exit_code = worker.run()
        if exit_code:
            raise SystemExit(exit_code)
