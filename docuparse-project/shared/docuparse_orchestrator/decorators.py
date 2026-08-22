from __future__ import annotations

import functools
import time
import traceback as traceback_module
import uuid
from typing import Any, Callable, TypeVar

from opentelemetry import trace
from tenacity import Retrying, stop_after_attempt, wait_exponential

from docuparse_orchestrator._run_context import current_run_errors, current_run_id
from docuparse_orchestrator.persistence import TaskExecutionWriter, default_django_writer
from docuparse_orchestrator.results import TaskError, TaskResult

_tracer = trace.get_tracer(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def task(
    name: str | None = None,
    *,
    max_attempts: int = 3,
    writer: TaskExecutionWriter = default_django_writer,
) -> Callable[[F], F]:
    """Envolve `func` como uma task rastreável: span por execução, retry com
    backoff exponencial via `tenacity`, e um `TaskExecution` gravado por
    tentativa final (sucesso ou esgotamento de retries) — nunca por tentativa
    intermediária. Nunca levanta: quem decide se a cadeia continua é o
    orquestrador, inspecionando `TaskResult.status`, não o decorator."""

    def decorator(func: F) -> F:
        task_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> TaskResult:
            run_id = current_run_id.get() or str(uuid.uuid4())
            attempt = 0
            started = time.monotonic()

            with _tracer.start_as_current_span(f"task.{task_name}"):
                try:
                    payload: Any = None
                    for attempt_state in Retrying(
                        stop=stop_after_attempt(max_attempts),
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
