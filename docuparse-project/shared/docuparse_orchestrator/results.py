from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class TaskError:
    type: str
    message: str
    traceback: str


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
