"""
DebouncedQueue v2

Fila com debounce genérica, tipagem forte, backends plugáveis.

Novidades v2:
  - MemoryBackend   — zero dependências, ideal para testes e desenvolvimento
  - max_wait        — flush forçado após N segundos mesmo sem silêncio
  - on_error        — callback assíncrono para falhas no handler
  - CeleryBackend   — push-based, sem polling loop; o Celery gerencia o timing

Backends:
  ┌─────────────────┬───────────────────────────────────────────────────┐
  │ MemoryBackend   │ dict em memória, sem I/O. Testes/dev.             │
  │ PostgresBackend │ UPSERT + SKIP LOCKED. Pull-based (loop interno).  │
  │ CeleryBackend   │ Redis acumula, Celery dispara. Push-based.        │
  └─────────────────┴───────────────────────────────────────────────────┘

Exemplo mínimo:
    queue = DebouncedQueue(
        schema=IncomingMessage,
        key_fn=lambda m: m.conversation_id,
        on_flush=handle_turn,
        backend=PostgresBackend(pool=pg_pool),
        delay=3.0,
        max_wait=30.0,
        on_error=my_error_handler,
    )
    await queue.start()
    await queue.enqueue(IncomingMessage(...))
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import time
from abc import ABC
from abc import abstractmethod
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import Generic
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Serialização genérica
# ---------------------------------------------------------------------------


def _serialize(item: Any) -> str:
    if isinstance(item, BaseModel):
        return item.model_dump_json()
    if dataclasses.is_dataclass(item) and not isinstance(item, type):
        return json.dumps(dataclasses.asdict(item))
    raise TypeError(f"Tipo não suportado: {type(item)}. Use BaseModel ou dataclass.")


def _deserialize(schema: type[T], raw: str) -> T:
    data = json.loads(raw)
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        return schema.model_validate(data)  # type: ignore[return-value]
    if dataclasses.is_dataclass(schema):
        return schema(**data)  # type: ignore[return-value]
    raise TypeError(f"Schema não suportado: {schema}")


# ---------------------------------------------------------------------------
# Interface base
# ---------------------------------------------------------------------------


class QueueBackend(ABC, Generic[T]):
    """
    Interface de backend. Dois modelos de operação:

    Pull-based (MemoryBackend, PostgresBackend):
        O DebouncedQueue chama flush_ready() a cada tick.

    Push-based (CeleryBackend):
        O backend agenda o flush internamente via Celery.
        flush_ready() sempre retorna [].
        O backend recebe um executor via set_flush_executor() e o chama
        diretamente quando a task Celery dispara.
    """

    @abstractmethod
    async def push(self, key: str, serialized_item: str) -> None:
        """Acumula item. Deve ser não-bloqueante (<5ms)."""
        ...

    @abstractmethod
    async def flush_ready(
        self,
        delay: float,
        max_wait: float | None,
    ) -> list[tuple[str, list[str]]]:
        """
        Retorna e remove grupos prontos.
        Um grupo está pronto se:
          - ficou silencioso por `delay` segundos, OU
          - existe há mais de `max_wait` segundos (se max_wait não for None).
        Retorna lista de (key, [serialized_item, ...]).
        """
        ...

    def set_flush_executor(
        self,
        executor: Callable[[str, list[str]], Awaitable[None]],
    ) -> None:
        """
        Push-based backends usam isso para receber o executor do DebouncedQueue
        e chamá-lo diretamente quando o Celery task disparar.
        Pull-based backends ignoram.
        """


# ---------------------------------------------------------------------------
# MemoryBackend
# ---------------------------------------------------------------------------


class MemoryBackend(QueueBackend[T]):
    """
    Backend em memória. Zero dependências externas.

    Ideal para:
      - Testes unitários (sem Postgres nem Redis)
      - Desenvolvimento local
      - Processos single-worker onde persistência não é crítica

    NÃO use em produção multi-worker: o estado é local ao processo.
    """

    def __init__(self) -> None:
        # key → {"items": [...], "first_at": float, "last_at": float}
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def push(self, key: str, serialized_item: str) -> None:
        async with self._lock:
            now = time.monotonic()
            if key not in self._store:
                self._store[key] = {"items": [], "first_at": now, "last_at": now}
            self._store[key]["items"].append(serialized_item)
            self._store[key]["last_at"] = now

    async def flush_ready(
        self,
        delay: float,
        max_wait: float | None,
    ) -> list[tuple[str, list[str]]]:
        async with self._lock:
            now = time.monotonic()
            ready: list[tuple[str, list[str]]] = []
            keys_to_remove: list[str] = []

            for key, entry in self._store.items():
                silent_enough = (now - entry["last_at"]) >= delay
                waited_too_long = (
                    max_wait is not None and (now - entry["first_at"]) >= max_wait
                )
                if silent_enough or waited_too_long:
                    ready.append((key, list(entry["items"])))
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._store[key]

            return ready

    def pending_keys(self) -> list[str]:
        """Utilitário para testes: retorna keys ainda no buffer."""
        return list(self._store.keys())


# ---------------------------------------------------------------------------
# PostgresBackend
# ---------------------------------------------------------------------------

SETUP_SQL = """
CREATE TABLE IF NOT EXISTS debounced_queue (
    queue_name      TEXT        NOT NULL,
    queue_key       TEXT        NOT NULL,
    items           JSONB       NOT NULL DEFAULT '[]'::jsonb,
    enqueued_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (queue_name, queue_key)
);
CREATE INDEX IF NOT EXISTS idx_debounced_queue_updated
    ON debounced_queue (queue_name, last_updated_at);
CREATE INDEX IF NOT EXISTS idx_debounced_queue_enqueued
    ON debounced_queue (queue_name, enqueued_at);
"""

PUSH_SQL = """
INSERT INTO debounced_queue (queue_name, queue_key, items, enqueued_at)
VALUES ($1, $2, jsonb_build_array($3::jsonb), now())
ON CONFLICT (queue_name, queue_key)
DO UPDATE SET
    items           = debounced_queue.items || jsonb_build_array(EXCLUDED.items->0),
    last_updated_at = now();
"""

# Flush por delay (silêncio) OU por max_wait (tempo máximo de espera).
# $4 = max_wait em segundos como TEXT, ou NULL para desativar max_wait.
FLUSH_SQL = """
WITH ready AS (
    SELECT queue_key, items
    FROM debounced_queue
    WHERE queue_name = $1
      AND (
          last_updated_at < now() - ($2 || ' seconds')::interval
          OR (
              $4::text IS NOT NULL
              AND enqueued_at < now() - ($4 || ' seconds')::interval
          )
      )
    ORDER BY last_updated_at
    LIMIT $3
    FOR UPDATE SKIP LOCKED
)
DELETE FROM debounced_queue d
USING ready
WHERE d.queue_name = $1
  AND d.queue_key  = ready.queue_key
RETURNING ready.queue_key, ready.items;
"""


class PostgresBackend(QueueBackend[T]):
    """
    Backend Postgres. Pull-based: DebouncedQueue chama flush_ready() a cada tick.

    Destaques:
      - UPSERT acumula itens atomicamente (sem race condition no push)
      - SKIP LOCKED permite múltiplos workers sem deadlock
      - enqueued_at rastreia quando o grupo começou (para max_wait)
      - last_updated_at rastreia o último evento (para delay)

    Parâmetros:
        pool        — asyncpg.Pool já criado.
        queue_name  — namespace (múltiplas filas na mesma tabela).
        batch_size  — máximo de keys por flush tick (default 50).
    """

    def __init__(
        self,
        pool: Any,
        queue_name: str = "default",
        batch_size: int = 50,
    ) -> None:
        self._pool = pool
        self._queue_name = queue_name
        self._batch_size = batch_size

    async def setup(self) -> None:
        """Cria a tabela se não existir. Chame uma vez no startup."""
        async with self._pool.acquire() as conn:
            await conn.execute(SETUP_SQL)

    async def push(self, key: str, serialized_item: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(PUSH_SQL, self._queue_name, key, serialized_item)

    async def flush_ready(
        self,
        delay: float,
        max_wait: float | None,
    ) -> list[tuple[str, list[str]]]:
        max_wait_str = str(max_wait) if max_wait is not None else None
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                FLUSH_SQL,
                self._queue_name,
                str(delay),
                self._batch_size,
                max_wait_str,
            )
        return [
            (row["queue_key"], [json.dumps(item) for item in row["items"]])
            for row in rows
        ]


# ---------------------------------------------------------------------------
# CeleryBackend
# ---------------------------------------------------------------------------


class CeleryBackend(QueueBackend[T]):
    """
    Backend Redis + Celery. Push-based: cada push() agenda um Celery task.

    Como funciona:
        1. push() acumula o item em uma Redis list para a key.
        2. Revoga o Celery task anterior dessa key (se existir).
        3. Agenda um novo task com countdown=delay — reinicia o timer.
        4. Quando o countdown expira sem novos eventos, o task executa:
           a. Verifica timestamp guard (descarta se chegou evento mais novo).
           b. Faz LRANGE + DELETE atômico no Redis.
           c. Chama o executor (on_flush do DebouncedQueue).

    max_wait:
        No primeiro push() de um grupo, agenda um segundo task com
        countdown=max_wait e task_id fixo. Esse task usa o mesmo timestamp
        guard — se o flush já ocorreu via delay normal, ele aborta sem-op.

    Diferença fundamental vs PostgresBackend:
        - PostgresBackend: loop ativo no processo FastAPI (asyncio task).
        - CeleryBackend:   timing gerenciado pelos workers Celery.
          Ideal quando você já tem infraestrutura Celery rodando.

    IMPORTANTE: Chame register_tasks() uma vez, em um módulo importado
    pelos Celery workers (ex: tasks.py):

        backend = CeleryBackend(redis_client, celery_app, delay=3.0)
        backend.register_tasks()

    Parâmetros:
        redis_client  — redis.asyncio.Redis (async, para FastAPI).
        celery_app    — instância Celery.
        queue_name    — prefixo das chaves Redis.
        delay         — debounce delay (precisa ser conhecido no push).
        max_wait      — tempo máximo antes de forçar flush. None = sem limite.
    """

    def __init__(
        self,
        redis_client: Any,
        celery_app: Any,
        queue_name: str = "default",
        delay: float = 3.0,
        max_wait: float | None = None,
    ) -> None:
        self._redis = redis_client
        self._celery = celery_app
        self._queue_name = queue_name
        self._delay = delay
        self._max_wait = max_wait
        self._executor: Callable[[str, list[str]], Awaitable[None]] | None = None
        self._flush_task: Any = None  # preenchido por register_tasks()

    # --- chaves Redis ---

    def _items_key(self, key: str) -> str:
        return f"dq:{self._queue_name}:items:{key}"

    def _ts_key(self, key: str) -> str:
        return f"dq:{self._queue_name}:ts:{key}"

    def _task_id_key(self, key: str) -> str:
        return f"dq:{self._queue_name}:task:{key}"

    def _maxwait_task_id_key(self, key: str) -> str:
        return f"dq:{self._queue_name}:mwtask:{key}"

    # --- interface QueueBackend ---

    def set_flush_executor(
        self,
        executor: Callable[[str, list[str]], Awaitable[None]],
    ) -> None:
        self._executor = executor

    async def push(self, key: str, serialized_item: str) -> None:
        if self._flush_task is None:
            raise RuntimeError(
                "CeleryBackend: chame register_tasks() antes de usar enqueue()."
            )

        ts = time.time()

        # 1. acumula no Redis
        pipe = self._redis.pipeline()
        pipe.rpush(self._items_key(key), serialized_item)
        pipe.set(self._ts_key(key), ts)
        pipe.expire(self._items_key(key), 3600)
        pipe.expire(self._ts_key(key), 3600)
        await pipe.execute()

        # 2. revoga task de debounce anterior e agenda novo (reinicia o timer)
        old_task_id_raw = await self._redis.get(self._task_id_key(key))
        if old_task_id_raw:
            self._celery.control.revoke(old_task_id_raw.decode(), terminate=False)

        new_task_id = f"dq-{self._queue_name}-{key}-{ts}"
        self._flush_task.apply_async(
            args=[key, ts, False],  # is_maxwait=False
            countdown=self._delay,
            task_id=new_task_id,
        )
        await self._redis.set(self._task_id_key(key), new_task_id, ex=3600)

        # 3. agenda task de max_wait apenas se for a primeira mensagem do grupo
        if self._max_wait is not None:
            existing_mw = await self._redis.get(self._maxwait_task_id_key(key))
            if not existing_mw:
                mw_task_id = f"dq-{self._queue_name}-{key}-maxwait-{ts}"
                self._flush_task.apply_async(
                    args=[key, ts, True],  # is_maxwait=True
                    countdown=self._max_wait,
                    task_id=mw_task_id,
                )
                await self._redis.set(
                    self._maxwait_task_id_key(key),
                    mw_task_id,
                    ex=int(self._max_wait) + 300,
                )

    async def flush_ready(
        self,
        delay: float,
        max_wait: float | None,
    ) -> list[tuple[str, list[str]]]:
        # Push-based: o Celery gerencia o timing. O loop do DebouncedQueue
        # chama isso mas sempre recebe lista vazia — sem overhead.
        return []

    def register_tasks(self) -> None:
        """
        Registra o Celery task nesta instância.
        Chame uma vez em tasks.py (ou onde o worker importa).

        O task é SÍNCRONO por design (padrão Celery).
        Usa asyncio.run() para chamar o executor assíncrono do DebouncedQueue.

        Se seu worker usa gevent ou eventlet, substitua asyncio.run() por:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(...)
        """
        backend = self

        @self._celery.task(
            name=f"debounced_queue.flush.{self._queue_name}",
            bind=True,
            acks_late=True,  # confirma só após execução (mais seguro)
            max_retries=3,
            default_retry_delay=5,
        )
        def flush_task(
            self_task: Any,
            key: str,
            scheduled_ts: float,
            is_maxwait: bool,
        ) -> None:
            """
            Executa o flush de uma key.

            is_maxwait=False → task de debounce normal (agendado com countdown=delay).
            is_maxwait=True  → task de segurança (agendado com countdown=max_wait).
            Ambos usam o mesmo código — o timestamp guard cuida da lógica.
            """
            import redis as sync_redis  # cliente síncrono para dentro do worker

            # Reconstrói URL do Redis a partir do cliente async
            # Ajuste conforme sua configuração (URL, host/port, etc.)
            redis_url = getattr(
                backend._redis, "_redis_url", "redis://localhost:6379/0"
            )
            sync_r = sync_redis.from_url(redis_url)

            try:
                # --- timestamp guard ---
                # Se chegou um evento mais novo DEPOIS que esta task foi agendada,
                # uma task mais recente vai processar. Esta aborta.
                current_ts_raw = sync_r.get(backend._ts_key(key))
                if current_ts_raw:
                    current_ts = float(current_ts_raw)
                    if current_ts > scheduled_ts + 0.01:  # 10ms de tolerância
                        logger.debug(
                            "Task obsoleta para key=%s (scheduled=%.3f < current=%.3f)",
                            key,
                            scheduled_ts,
                            current_ts,
                        )
                        return

                # --- fetch e limpeza atômica ---
                pipe = sync_r.pipeline()
                pipe.lrange(backend._items_key(key), 0, -1)
                pipe.delete(
                    backend._items_key(key),
                    backend._ts_key(key),
                    backend._task_id_key(key),
                    backend._maxwait_task_id_key(key),
                )
                raw_items: list[bytes] = pipe.execute()[0]

                if not raw_items:
                    return  # outro worker já processou

                serialized = [item.decode() for item in raw_items]

                # --- chama o executor assíncrono ---
                if backend._executor is not None:
                    asyncio.run(backend._executor(key, serialized))
                else:
                    logger.warning(
                        "CeleryBackend: executor não configurado para key=%s. "
                        "Certifique-se de usar DebouncedQueue ou chamar "
                        "set_flush_executor() manualmente.",
                        key,
                    )

            except Exception as exc:
                logger.exception("Erro no flush_task Celery para key=%s", key)
                raise self_task.retry(exc=exc)

        self._flush_task = flush_task


# ---------------------------------------------------------------------------
# DebouncedQueue
# ---------------------------------------------------------------------------


class DebouncedQueue(Generic[T]):
    """
    Orquestrador genérico de debounce.

    Parâmetros:
        schema      — BaseModel ou dataclass. Define a tipagem dos itens.
        key_fn      — extrai a chave de debounce do item.
        on_flush    — coroutine chamada com (key, items) no flush.
        backend     — MemoryBackend, PostgresBackend ou CeleryBackend.
        delay       — segundos de silêncio antes do flush (default 3.0).
        max_wait    — flush forçado após N segundos de atividade contínua.
                      Evita starvation em conversas muito longas. (default None)
        on_error    — coroutine chamada com (key, items, exc) em falha no
                      on_flush. Se None, apenas loga o erro.
        tick        — intervalo do loop de flush em segundos (default 1.0).
                      Ignorado por CeleryBackend (push-based).
    """

    def __init__(
        self,
        schema: type[T],
        key_fn: Callable[[T], str],
        on_flush: Callable[[str, list[T]], Awaitable[None]],
        backend: QueueBackend[T],
        delay: float = 3.0,
        max_wait: float | None = None,
        on_error: Callable[[str, list[T], Exception], Awaitable[None]] | None = None,
        tick: float = 1.0,
    ) -> None:
        if max_wait is not None and max_wait <= delay:
            raise ValueError(
                f"max_wait ({max_wait}s) deve ser maior que delay ({delay}s)."
            )

        self._schema = schema
        self._key_fn = key_fn
        self._on_flush = on_flush
        self._backend = backend
        self._delay = delay
        self._max_wait = max_wait
        self._on_error = on_error
        self._tick = tick
        self._running = False
        self._task: asyncio.Task[None] | None = None

        # Injeta o executor no backend (CeleryBackend usa isso)
        self._backend.set_flush_executor(self._execute_serialized)

    # --- API pública ---

    async def enqueue(self, item: T) -> None:
        """
        Enfileira um item. Retorna imediatamente (<5ms).
        Seguro para hot paths (ex: webhook handler).
        """
        key = self._key_fn(item)
        serialized = _serialize(item)
        await self._backend.push(key, serialized)

    async def start(self) -> None:
        """Inicia o flush loop em background (pull-based backends)."""
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="debounced_queue_loop")
        logger.info(
            "DebouncedQueue iniciada | delay=%.1fs | max_wait=%s | tick=%.1fs | backend=%s",
            self._delay,
            f"{self._max_wait}s" if self._max_wait else "∞",
            self._tick,
            type(self._backend).__name__,
        )

    async def stop(self) -> None:
        """Para o loop e executa um flush final dos itens pendentes."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("DebouncedQueue: flush final antes de encerrar...")
        await self._flush_once()
        logger.info("DebouncedQueue encerrada.")

    async def flush_now(self) -> None:
        """Força flush imediato. Útil em testes e shutdown."""
        await self._flush_once()

    # --- internos ---

    async def _loop(self) -> None:
        while self._running:
            await self._flush_once()
            await asyncio.sleep(self._tick)

    async def _flush_once(self) -> None:
        try:
            groups = await self._backend.flush_ready(self._delay, self._max_wait)
        except Exception:
            logger.exception("DebouncedQueue: erro ao buscar grupos prontos")
            return

        if groups:
            await asyncio.gather(
                *[self._process_group(key, raw_items) for key, raw_items in groups],
                return_exceptions=True,
            )

    async def _process_group(self, key: str, raw_items: list[str]) -> None:
        items = [_deserialize(self._schema, r) for r in raw_items]
        await self._execute(key, items)

    async def _execute(self, key: str, items: list[T]) -> None:
        try:
            await self._on_flush(key, items)
        except Exception as exc:
            logger.exception("DebouncedQueue: erro no on_flush para key=%s", key)
            if self._on_error is not None:
                try:
                    await self._on_error(key, items, exc)
                except Exception:
                    logger.exception(
                        "DebouncedQueue: erro no próprio on_error para key=%s", key
                    )

    async def _execute_serialized(self, key: str, raw_items: list[str]) -> None:
        """Executor injetado no CeleryBackend."""
        await self._process_group(key, raw_items)
