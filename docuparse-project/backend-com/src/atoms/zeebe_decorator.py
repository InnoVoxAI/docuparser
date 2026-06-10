import asyncio
import inspect
import logging
import traceback
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError
from pyzeebe import create_insecure_channel
from pyzeebe import ZeebeWorker as _ZeebeWorker


logger = logging.getLogger("zeebe_worker")
logging.basicConfig(level=logging.INFO)


def build_kwargs(variables: dict[str, Any], sig: inspect.Signature) -> dict[str, Any]:
    kwargs = {}

    for name, param in sig.parameters.items():
        annotation = param.annotation
        raw_value = variables.get(name)

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            if raw_value is None:
                raise ValueError(f"Missing required input model: {name}")
            kwargs[name] = annotation(**raw_value)

        elif annotation in (int, float, str, bool):
            kwargs[name] = annotation(raw_value) if raw_value is not None else None

        elif callable(annotation) and annotation is not inspect.Parameter.empty:
            kwargs[name] = annotation(raw_value) if raw_value is not None else None

        else:
            kwargs[name] = raw_value

    return kwargs


def serialize_result(result: Any) -> dict[str, Any]:
    if result is None:
        return {}
    if isinstance(result, BaseModel):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return {"result": result}


class ZeebeWorker:
    def __init__(
        self,
        hostname: str = "localhost",
        port: int = 26500,
        worker_id: str = "worker",
    ):
        self.hostname = hostname
        self.port = port
        self.worker_id = worker_id
        self._handlers: list[tuple[str, Callable, inspect.Signature]] = []

    def subscribe(self, fn: Callable) -> "ZeebeWorker":
        if not hasattr(fn, "_camunda_topic"):
            raise ValueError(
                f"Function '{fn.__name__}' must be decorated with @camunda_task"
            )

        topic = getattr(fn, "_camunda_topic")
        sig = inspect.signature(fn)
        self._handlers.append((topic, fn, sig))
        return self

    def start(self):
        if not self._handlers:
            raise RuntimeError("No handlers registered")

        asyncio.run(self._run())

    async def _run(self):
        channel = create_insecure_channel(grpc_address=f"{self.hostname}:{self.port}")
        worker = _ZeebeWorker(channel)

        for topic, fn, sig in self._handlers:
            _register_task(worker, topic, fn, sig)
            logger.info(f"Starting worker for topic '{topic}'")

        logger.info("All workers started")
        await worker.work()


def _register_task(
    worker: _ZeebeWorker,
    topic: str,
    fn: Callable,
    sig: inspect.Signature,
):
    @worker.task(task_type=topic)
    async def handler(**variables):
        logger.info(f"[{topic}] Received job")
        try:
            kwargs = build_kwargs(variables, sig)
            result = fn(**kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            output = serialize_result(result)
            logger.info(f"[{topic}] Completed job")
            return output
        except ValidationError as ve:
            logger.error(f"[{topic}] Validation error: {ve}")
            raise
        except Exception as e:
            logger.error(f"[{topic}] Execution error: {e}")
            logger.debug(traceback.format_exc())
            raise
