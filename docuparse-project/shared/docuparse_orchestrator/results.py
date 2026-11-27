from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class TaskError:
    type: str
    message: str
    traceback: str
    # True quando a exceção é de um dos tipos em `retry_on` do @task, ou seja,
    # transitória. A fila durável (jobqueue) lê isso para decidir entre
    # reagendar e falhar, já que o decorator nunca levanta exceção.
    retryable: bool = False


@dataclass
class TaskResult:
    status: Literal["ok", "error"]
    payload: dict[str, Any] = field(default_factory=dict)
    error: TaskError | None = None
    task_name: str = ""
    task_id: str = ""
    run_id: str = ""
    attempt: int = 1
    duration_ms: int = 0
