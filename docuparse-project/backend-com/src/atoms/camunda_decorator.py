import inspect
import logging
import threading
import traceback
from collections.abc import Callable
from typing import Any

from camunda.external_task.external_task import ExternalTask
from camunda.external_task.external_task import TaskResult
from camunda.external_task.external_task_worker import ExternalTaskWorker
from pydantic import BaseModel
from pydantic import ValidationError


logger = logging.getLogger("camunda_worker")
logging.basicConfig(level=logging.INFO)


# ---------------------------
# Decorator
# ---------------------------


def camunda_task(topic_name: str):
    def decorator(fn: Callable):
        setattr(fn, "_camunda_topic", topic_name)
        return fn

    return decorator


# ---------------------------
# Utilities
# ---------------------------


def is_pydantic_model(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def build_kwargs(task: ExternalTask, sig: inspect.Signature) -> dict[str, Any]:
    kwargs = {}

    for name, param in sig.parameters.items():
        annotation = param.annotation
        raw_value = task.get_variable(name)

        # Pydantic model (preferred)
        if is_pydantic_model(annotation):
            if raw_value is None:
                raise ValueError(f"Missing required input model: {name}")
            kwargs[name] = annotation(**raw_value)

        # Primitive types
        elif annotation in (int, float, str, bool):
            if raw_value is not None:
                kwargs[name] = annotation(raw_value)
            else:
                kwargs[name] = None

        # Any other callable type — attempt construction (e.g. SecretStr, UUID, Enum)
        elif callable(annotation) and annotation is not inspect.Parameter.empty:
            kwargs[name] = annotation(raw_value) if raw_value is not None else None

        # No annotation — pass through as-is
        else:
            kwargs[name] = raw_value

    return kwargs


def serialize_result(result: Any) -> dict[str, Any]:
    if result is None:
        return {}

    if isinstance(result, BaseModel):
        return result.model_dump() if hasattr(result, "model_dump") else result.dict()

    if isinstance(result, dict):
        return result

    # fallback: wrap
    return {"result": result}


# ---------------------------
# Worker
# ---------------------------


class CamundaWorker:
    def __init__(
        self,
        base_url: str,
        worker_id: str = "worker",
        max_retries: int = 3,
        retry_timeout: int = 5000,
    ):
        self.base_url = base_url
        self.worker_id = worker_id
        self.max_retries = max_retries
        self.retry_timeout = retry_timeout

        self._handlers: list[tuple[str, Callable]] = []
        self._threads: list[threading.Thread] = []

    # ---------------------------
    # Registration
    # ---------------------------

    def subscribe(self, fn: Callable):
        if not hasattr(fn, "_camunda_topic"):
            raise ValueError(
                f"Function '{fn.__name__}' must be decorated with @camunda_task"
            )

        topic = getattr(fn, "_camunda_topic")
        sig = inspect.signature(fn)

        def handler(task: ExternalTask) -> TaskResult:
            try:
                logger.info(f"[{topic}] Received task {task.get_task_id()}")

                kwargs = build_kwargs(task, sig)

                result = fn(**kwargs)

                variables = serialize_result(result)

                logger.info(f"[{topic}] Completed task {task.get_task_id()}")

                return task.complete(variables)

            except ValidationError as ve:
                logger.error(f"[{topic}] Validation error: {ve}")

                return task.failure(
                    error_message="ValidationError",
                    error_details=str(ve),
                    retry_timeout=0,
                    max_retries=0,
                )

            except Exception as e:
                logger.error(f"[{topic}] Execution error: {e}")
                logger.debug(traceback.format_exc())

                return task.failure(
                    error_message=str(e),
                    error_details=traceback.format_exc(),
                    max_retries=self.max_retries,
                    retry_timeout=self.retry_timeout,
                )

        self._handlers.append((topic, handler))
        return self

    # ---------------------------
    # Execution
    # ---------------------------

    def _start_topic_worker(self, topic: str, handler: Callable, index: int):
        worker = ExternalTaskWorker(
            worker_id=f"{self.worker_id}_{index}",
            base_url=self.base_url,
        )

        logger.info(f"Starting worker for topic '{topic}'")

        worker.subscribe(topic, handler)

    def start(self):
        if not self._handlers:
            raise RuntimeError("No handlers registered")

        for i, (topic, handler) in enumerate(self._handlers):
            t = threading.Thread(
                target=self._start_topic_worker,
                args=(topic, handler, i),
                daemon=False,  # important for proper lifecycle
            )
            t.start()
            self._threads.append(t)

        logger.info("All workers started")

        # Block cleanly
        for t in self._threads:
            t.join()
