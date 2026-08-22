from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace

from docuparse_orchestrator._run_context import current_run_errors, current_run_id
from docuparse_orchestrator.persistence import (
    OrchestrationRunWriter,
    default_django_run_writer,
)

_tracer = trace.get_tracer(__name__)


@contextmanager
def orchestration_run(
    name: str,
    *,
    run_id: str | None = None,
    link: trace.Link | None = None,
    writer: OrchestrationRunWriter = default_django_run_writer,
) -> Iterator[str]:
    """Abre uma execução rastreável: todo `@task` chamado dentro deste bloco
    compartilha o `run_id` gerado aqui (contextvar, não o trace_id do OTel —
    ver ponto (c) do plano). Fecha como FAILED se uma exceção propagar OU se
    qualquer `@task` chamado dentro do bloco tiver terminado em erro — mesmo
    que o código orquestrador não tenha levantado nada (ex.: só fez
    `if status.status == "error": return`). Sem isso, um `@task` que falhou
    mas cujo chamador não re-levanta deixaria o run marcado COMPLETED por
    engano; não depende de ninguém lembrar de sinalizar a falha manualmente.
    `link` permite linkar o span raiz a um trace de origem que não é o pai
    direto (ex.: request que disparou este processamento em outra thread —
    mesmo padrão já usado em `processing_queue.capture_current_span_link`)."""
    resolved_run_id = run_id or str(uuid.uuid4())
    run_token = current_run_id.set(resolved_run_id)
    task_errors: list = []
    errors_token = current_run_errors.set(task_errors)
    writer.start(resolved_run_id, name)

    try:
        with _tracer.start_as_current_span(
            f"orchestration.{name}", links=[link] if link else []
        ):
            try:
                yield resolved_run_id
            except Exception:
                writer.finish(resolved_run_id, status="FAILED")
                raise
            else:
                writer.finish(
                    resolved_run_id,
                    status="FAILED" if task_errors else "COMPLETED",
                )
    finally:
        current_run_id.reset(run_token)
        current_run_errors.reset(errors_token)
