"""
Guia de integração: DebouncedQueue + CeleryBackend
====================================================

POR QUE O CeleryBackend É DIFERENTE DOS OUTROS
───────────────────────────────────────────────
MemoryBackend e PostgresBackend usam um loop de polling:

    while True:
        grupos = await backend.flush_ready(delay)   # verifica quem está pronto
        for grupo in grupos:
            await on_flush(grupo)
        await asyncio.sleep(tick)

O loop roda dentro do processo FastAPI. É simples, mas tem duas limitações:
  1. Latência mínima de `tick` segundos entre o debounce expirar e o flush.
  2. Tudo roda no mesmo processo — se o FastAPI reiniciar, items em voo são perdidos.

O CeleryBackend troca o polling por eventos:

    push() → agenda task Celery com countdown=delay → worker executa no momento certo

Não há polling. A task dispara exatamente quando o debounce expira.
O worker é um processo separado — resiliente a restarts do FastAPI.


ESTRUTURA DO PROJETO
────────────────────
myapp/
├── celery_app.py      ← instância Celery + configuração
├── tasks.py           ← registro das tasks (importado por FastAPI E worker)
├── main.py            ← FastAPI app
└── handlers.py        ← lógica de negócio (on_flush, on_error)


PASSO 1 — celery_app.py
"""

# celery_app.py
from celery import Celery

celery_app = Celery(
    "myapp",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    task_acks_late=True,          # confirma só após execução (mais seguro)
    worker_prefetch_multiplier=1, # evita que o worker pegue tasks demais
)


"""
PASSO 2 — tasks.py

Este arquivo é importado tanto pelo FastAPI quanto pelo worker Celery.
É aqui que o backend, o schema e o handler se encontram.
"""

# tasks.py
import redis.asyncio as aioredis
from pydantic import BaseModel

from debounced_queue import CeleryBackend, make_celery_flush_task
# from myapp.celery_app import celery_app  # import real

REDIS_URL = "redis://localhost:6379/0"


class IncomingMessage(BaseModel):
    conversation_id: str
    phone: str
    text: str
    timestamp: float


# Cliente async — usado pelo FastAPI no push()
redis_async = aioredis.from_url(REDIS_URL)

# Backend — instância única compartilhada
backend: CeleryBackend[IncomingMessage] = CeleryBackend(
    redis_async=redis_async,
    celery_app=celery_app,   # type: ignore
    redis_url=REDIS_URL,
    queue_name="whatsapp",
    delay=3.0,
)


# Handler SÍNCRONO — chamado pelo Celery worker
# O worker é um processo Python comum, sem event loop ativo.
# Para chamar código async, use use_async=True (ver abaixo).
def handle_turn_sync(key: str, messages: list[IncomingMessage]) -> None:
    turn_text = "\n".join(m.text for m in messages)
    print(f"[{key}] processando {len(messages)} mensagem(ns):\n{turn_text}")
    # aqui você pode:
    #   - chamar uma API HTTP de forma síncrona (requests.post)
    #   - delegar para outra Celery task que faz a chamada ao LLM
    #   - usar asyncio.run() para chamar código async pontualmente


# Handler ASYNC — use use_async=True
async def handle_turn_async(key: str, messages: list[IncomingMessage]) -> None:
    turn_text = "\n".join(m.text for m in messages)
    # await kai_mind.chat(key, turn_text)
    # await whatsapp_api.send(messages[0].phone, response)
    print(f"[async] {key}: {turn_text}")


# Registra a task — isso cria "dq_flush_whatsapp" no Celery
flush_task = make_celery_flush_task(
    celery_app=celery_app,      # type: ignore
    backend=backend,
    schema=IncomingMessage,
    handler=handle_turn_async,
    use_async=True,             # handler é async
)

# Pronto. `backend._flush_task_name` agora é "dq_flush_whatsapp"
# e o push() vai agendar essa task automaticamente.


"""
PASSO 3 — main.py (FastAPI)
"""

# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

from debounced_queue import DebouncedQueue


# Queue com CeleryBackend — o loop de polling aqui é só fallback.
# Defina tick > delay para que o Celery seja a via primária.
queue: DebouncedQueue[IncomingMessage]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global queue

    queue = DebouncedQueue(
        schema=IncomingMessage,
        key_fn=lambda m: m.conversation_id,
        on_flush=handle_turn_async,
        backend=backend,      # type: ignore
        delay=3.0,
        max_wait=30.0,        # flush forçado após 30s mesmo em conversa contínua
        on_error=on_flush_error,
        tick=10.0,            # loop roda a cada 10s — só fallback
    )
    await queue.start()

    yield

    await queue.stop()


app = FastAPI(lifespan=lifespan)


async def on_flush_error(key: str, items: list, exc: Exception) -> None:
    print(f"[ERRO] key={key} items={len(items)} exc={exc}")
    # aqui: salvar em dead-letter table, alertar Sentry, etc.


@app.post("/webhook/whatsapp")
async def webhook(request: Request):
    body = await request.json()

    try:
        entry = body["entry"][0]["changes"][0]["value"]
        raw   = entry["messages"][0]
        msg   = IncomingMessage(
            conversation_id=raw["from"],
            phone=raw["from"],
            text=raw["text"]["body"],
            timestamp=float(raw["timestamp"]),
        )
    except (KeyError, IndexError):
        return {"status": "ignored"}

    # Isso faz 3 coisas em < 5ms:
    #   1. rpush no Redis
    #   2. revoga task Celery anterior para este conversation_id
    #   3. agenda nova task com countdown=3s
    await queue.enqueue(msg)

    return {"status": "queued"}


"""
PASSO 4 — iniciar o worker

    # Terminal 1 — FastAPI
    uvicorn myapp.main:app --reload

    # Terminal 2 — Celery worker
    celery -A myapp.tasks worker --loglevel=info

    # Terminal 3 — Flower (monitoramento, opcional)
    celery -A myapp.tasks flower


FLUXO COMPLETO
──────────────

    t=0.0s  msg "oi"            → push() → task T1 agendada (countdown=3s)
    t=0.8s  msg "tudo bem?"     → push() → revoga T1, agenda T2 (countdown=3s)
    t=1.5s  msg "preciso ajuda" → push() → revoga T2, agenda T3 (countdown=3s)
    t=4.5s  T3 executa          → ts guard: ts_atual == scheduled_ts ✓
                                 → lrange ["oi", "tudo bem?", "preciso ajuda"]
                                 → handle_turn_async(key, [msg1, msg2, msg3])


GUARD DE STALENESS — POR QUE É NECESSÁRIO
──────────────────────────────────────────

O revoke() do Celery envia um sinal ao worker, mas NÃO é garantido
se a task já começou a executar. O guard de staleness protege:

    t=0.0s  push("oi")        → agenda T1 (ts=0.0, countdown=3s)
    t=2.9s  T1 começa a rodar no worker
    t=3.0s  push("mais info") → tenta revogar T1 (tarde demais) → agenda T2

    Sem guard: T1 processa ["oi"] com ts_atual=3.0 > scheduled_ts=0.0
               Guard detecta: ts_atual (3.0) > scheduled_ts (0.0) + 0.05 → descarta T1
    T2 vai processar ["oi", "mais info"] quando o countdown expirar.


QUANDO USAR CELERY vs POSTGRES
───────────────────────────────

    Use PostgresBackend quando:
    • Já usa Postgres e quer zero dependências extras
    • Volume moderado (< 1k mensagens/min)
    • Latência de flush de 1-2s é aceitável
    • Quer simplicidade operacional

    Use CeleryBackend quando:
    • Já tem Celery no stack (InnoVox/Paideia já têm)
    • Quer flush no momento exato do debounce (sem esperar o tick)
    • Handler é pesado e quer distribuir a carga entre workers
    • Quer retry automático em falhas (Celery trata isso nativamente)
    • Quer monitoramento visual via Flower


RETRY AUTOMÁTICO COM CELERY
────────────────────────────
O handler pode falhar (LLM timeout, WhatsApp API fora, etc.).
Com Celery, retry é nativo:

    @celery_app.task(name="dq_flush_whatsapp", bind=True,
                     autoretry_for=(Exception,),
                     retry_backoff=True,
                     max_retries=3)
    def flush_task(self, queue_name, key, scheduled_ts):
        ...

make_celery_flush_task() não seta retry automaticamente para não
esconder bugs silenciosamente. Configure na task retornada conforme
sua política de tolerância a falhas.
"""
