from __future__ import annotations

import functools
from typing import Any, Awaitable, Callable, TypeVar

from opentelemetry import propagate, trace
from opentelemetry.trace import Link

_tracer = trace.get_tracer(__name__)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def extract_trace_link_from_job(job_variables: dict[str, Any]) -> Link | None:
    """Extrai um `Link` a partir da variável `traceparent` de um job Zeebe.

    O `traceparent` (e `tracestate`, se presente) é serializado como variável
    de processo em `scripts/start_process.py` no início da instância BPMN
    (research.md R3). Retorna `None` quando a variável está ausente (processo
    iniciado antes desta feature, ou por um caminho ainda não instrumentado) —
    o worker deve então iniciar um trace novo e desconectado, em vez de falhar.
    """
    traceparent = job_variables.get("traceparent")
    if not traceparent:
        return None
    carrier = {"traceparent": traceparent}
    tracestate = job_variables.get("tracestate")
    if tracestate:
        carrier["tracestate"] = tracestate
    context = propagate.extract(carrier)
    span_context = trace.get_current_span(context).get_span_context()
    if not span_context.is_valid:
        return None
    return Link(span_context)


def traced_job(job_type: str) -> Callable[[F], F]:
    """Decorator para job handlers Zeebe (`@*.task(task_type=job_type, ...)`).

    Inicia um span `zeebe.job.{job_type}` linkado (não parent-child, ver
    research.md R3) ao trace de origem quando o job carrega um `traceparent`.
    Preserva a assinatura da função decorada (via `functools.wraps`) para que
    a introspecção de parâmetros do pyzeebe continue funcionando normalmente.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            link = extract_trace_link_from_job(kwargs)
            with _tracer.start_as_current_span(
                f"zeebe.job.{job_type}", links=[link] if link else []
            ):
                return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
