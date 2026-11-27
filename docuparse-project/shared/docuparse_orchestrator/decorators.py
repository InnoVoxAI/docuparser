from __future__ import annotations

import functools
import time
import traceback as traceback_module
import uuid
from collections.abc import Callable
from typing import Any, TypeVar

from opentelemetry import trace
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from docuparse_orchestrator._run_context import current_run_errors, current_run_id
from docuparse_orchestrator.persistence import (
    TaskExecutionWriter,
    default_django_writer,
)
from docuparse_orchestrator.results import TaskError, TaskResult

_tracer = trace.get_tracer(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def task(
    name: str | None = None,
    *,
    max_attempts: int = 3,
    retry_on: tuple[type[BaseException], ...] = (),
    writer: TaskExecutionWriter = default_django_writer,
) -> Callable[[F], F]:
    """Envolve `func` como uma task rastreável: span por execução, retry com
    backoff exponencial via `tenacity`, e um `TaskExecution` gravado por
    tentativa final (sucesso, erro permanente ou esgotamento de retries) —
    nunca por tentativa intermediária. Nunca levanta: quem decide se a cadeia
    continua é o orquestrador, inspecionando `TaskResult.status`, não o
    decorator.

    Retry é opt-in (AR-27): só exceções de um dos tipos em `retry_on` são
    repetidas, até `max_attempts`. Qualquer outra exceção encerra na primeira
    tentativa. O padrão `()` não repete nada, porque repetir a função inteira
    refaz efeitos colaterais (chamada paga de OCR/LLM, gravações não
    idempotentes). Quem declara `retry_on` é o call site, com os tipos
    transitórios que os seus clientes levantam."""

    def decorator(func: F) -> F:
        task_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> TaskResult:
            # Fallback pra um run_id avulso quando chamado sem orchestration_run
            # ativa (ex.: script ad hoc, ou testes com um writer fake). Com o
            # writer Django real isso NÃO basta sozinho: default_django_writer
            # espera uma OrchestrationRun já existente com esse run_id (FK) —
            # todo call site real deve sempre chamar dentro de um
            # `with orchestration_run(...)` (ver documents/services/process_dashboard.py
            # `retry_step` pra um exemplo de task avulsa feita corretamente).
            run_id = current_run_id.get() or str(uuid.uuid4())
            attempt = 0
            started = time.monotonic()

            with _tracer.start_as_current_span(f"task.{task_name}"):
                try:
                    payload: Any = None
                    for attempt_state in Retrying(
                        stop=stop_after_attempt(max_attempts),
                        retry=retry_if_exception_type(retry_on),
                        wait=wait_exponential(multiplier=0.1, max=5),
                        reraise=True,
                    ):
                        with attempt_state:
                            started = time.monotonic()
                            attempt = attempt_state.retry_state.attempt_number
                            payload = func(*args, **kwargs)

                    result = TaskResult(
                        status="ok",
                        payload=payload if isinstance(payload, dict) else {},
                        task_name=task_name,
                        task_id=str(uuid.uuid4()),
                        run_id=run_id,
                        attempt=attempt,
                        duration_ms=int((time.monotonic() - started) * 1000),
                    )
                except Exception as exc:
                    result = TaskResult(
                        status="error",
                        payload={},
                        error=TaskError(
                            type=type(exc).__name__,
                            message=str(exc),
                            traceback=traceback_module.format_exc(),
                        ),
                        task_name=task_name,
                        task_id=str(uuid.uuid4()),
                        run_id=run_id,
                        attempt=attempt or 1,
                        duration_ms=int((time.monotonic() - started) * 1000),
                    )

            writer(result)
            if result.status == "error":
                errors = current_run_errors.get()
                if errors is not None:
                    errors.append(result)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
