"""
Exemplo: WhatsApp + FastAPI + DebouncedQueue + PostgresBackend
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

import asyncpg
from atoms.debounce.debounced_queue import DebouncedQueue
from atoms.debounce.debounced_queue import PostgresBackend
from fastapi import FastAPI
from fastapi import Request
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Schema — funciona igual com @dataclass
# ---------------------------------------------------------------------------


class IncomingMessage(BaseModel):
    conversation_id: str
    phone: str
    text: str
    timestamp: float


# ---------------------------------------------------------------------------
# Handler — chamado uma vez por grupo de mensagens
# ---------------------------------------------------------------------------


async def handle_conversation_turn(key: str, messages: list[IncomingMessage]) -> None:
    turn_text = "\n".join(m.text for m in messages)
    # phone = messages[0].phone

    print(f"[{key}] {len(messages)} mensagem(ns) → LLM:\n{turn_text}")

    # response = await kai_mind.chat(key, turn_text)
    # await whatsapp_api.send_message(phone, response)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

queue: DebouncedQueue[IncomingMessage]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global queue

    pool = await asyncpg.create_pool("postgresql://user:pass@localhost/db")
    backend = PostgresBackend(pool=pool, queue_name="whatsapp")
    await backend.setup()  # cria tabela se não existir

    queue = DebouncedQueue(
        schema=IncomingMessage,
        key_fn=lambda m: m.conversation_id,
        on_flush=handle_conversation_turn,
        backend=backend,
        delay=3.0,  # segundos de silêncio antes do flush
        tick=1.0,  # intervalo do loop
    )
    await queue.start()

    yield

    await queue.stop()
    await pool.close()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook/whatsapp")
async def webhook(request: Request):
    body = await request.json()

    # parse do payload real do WhatsApp Cloud API
    try:
        entry = body["entry"][0]["changes"][0]["value"]
        raw_msg = entry["messages"][0]

        msg = IncomingMessage(
            conversation_id=raw_msg["from"],  # ou thread_id se disponível
            phone=raw_msg["from"],
            text=raw_msg["text"]["body"],
            timestamp=float(raw_msg["timestamp"]),
        )
    except (KeyError, IndexError):
        return {"status": "ignored"}

    await queue.enqueue(msg)
    return {"status": "queued"}


# ---------------------------------------------------------------------------
# Exemplo com dataclass (drop-in, sem mudar o DebouncedQueue)
# ---------------------------------------------------------------------------
@dataclass
class AnalyticsEvent:
    user_id: str
    event: str
    value: float


async def handle_analytics(key: str, events: list[AnalyticsEvent]) -> None:
    total = sum(e.value for e in events)
    print(f"[analytics:{key}] {len(events)} eventos, total={total}")


analytics_queue = DebouncedQueue(
    schema=AnalyticsEvent,
    key_fn=lambda e: e.user_id,
    on_flush=handle_analytics,
    backend=PostgresBackend(pool=None, queue_name="analytics"),  # type: ignore
    delay=5.0,
)
