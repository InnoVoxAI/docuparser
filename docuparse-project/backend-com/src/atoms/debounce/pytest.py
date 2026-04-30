"""
Testes usando MemoryBackend — sem Postgres, sem Redis, sem Celery.
"""
import asyncio
from dataclasses import dataclass

import pytest
from atoms.debounce.debounced_queue import DebouncedQueue
from atoms.debounce.debounced_queue import MemoryBackend
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Schemas de teste
# ---------------------------------------------------------------------------


class Message(BaseModel):
    convo_id: str
    text: str


@dataclass
class Event:
    user_id: str
    value: float


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_debounce_acumula_e_faz_flush():
    """Mensagens fragmentadas chegam como lista completa no on_flush."""
    received: list[tuple[str, list[Message]]] = []

    async def on_flush(key: str, items: list[Message]) -> None:
        received.append((key, items))

    queue = DebouncedQueue(
        schema=Message,
        key_fn=lambda m: m.convo_id,
        on_flush=on_flush,
        backend=MemoryBackend(),
        delay=0.1,
        tick=0.05,
    )
    await queue.start()

    await queue.enqueue(Message(convo_id="c1", text="oi"))
    await queue.enqueue(Message(convo_id="c1", text="tudo bem?"))
    await queue.enqueue(Message(convo_id="c1", text="preciso de ajuda"))

    await asyncio.sleep(0.3)
    await queue.stop()

    assert len(received) == 1
    key, items = received[0]
    assert key == "c1"
    assert [m.text for m in items] == ["oi", "tudo bem?", "preciso de ajuda"]


@pytest.mark.asyncio
async def test_max_wait_flush_forcado():
    """max_wait força o flush mesmo com mensagens chegando continuamente."""
    received: list[tuple[str, list[Message]]] = []

    async def on_flush(key: str, items: list[Message]) -> None:
        received.append((key, items))

    queue = DebouncedQueue(
        schema=Message,
        key_fn=lambda m: m.convo_id,
        on_flush=on_flush,
        backend=MemoryBackend(),
        delay=10.0,  # delay enorme — não dispararia sem max_wait
        max_wait=0.2,  # mas max_wait é pequeno
        tick=0.05,
    )
    await queue.start()

    # Envia mensagens continuamente (reseta o delay a cada vez)
    for i in range(5):
        await queue.enqueue(Message(convo_id="c2", text=f"msg {i}"))
        await asyncio.sleep(0.05)

    await asyncio.sleep(0.3)
    await queue.stop()

    # max_wait forçou o flush mesmo sem silêncio
    assert len(received) >= 1
    assert received[0][0] == "c2"


@pytest.mark.asyncio
async def test_on_error_captura_excecao():
    """on_error é chamado quando on_flush levanta exceção."""
    errors: list[tuple[str, Exception]] = []

    async def on_flush(key: str, items: list[Message]) -> None:
        raise ValueError("LLM timeout")

    async def on_error(key: str, items: list[Message], exc: Exception) -> None:
        errors.append((key, exc))

    queue = DebouncedQueue(
        schema=Message,
        key_fn=lambda m: m.convo_id,
        on_flush=on_flush,
        on_error=on_error,
        backend=MemoryBackend(),
        delay=0.1,
        tick=0.05,
    )
    await queue.start()
    await queue.enqueue(Message(convo_id="c3", text="teste"))
    await asyncio.sleep(0.3)
    await queue.stop()

    assert len(errors) == 1
    assert errors[0][0] == "c3"
    assert isinstance(errors[0][1], ValueError)


@pytest.mark.asyncio
async def test_dataclass_funciona_igual():
    """Dataclass tem a mesma interface que BaseModel."""
    received: list[list[Event]] = []

    async def on_flush(key: str, items: list[Event]) -> None:
        received.append(items)

    queue = DebouncedQueue(
        schema=Event,
        key_fn=lambda e: e.user_id,
        on_flush=on_flush,
        backend=MemoryBackend(),
        delay=0.1,
        tick=0.05,
    )
    await queue.start()
    await queue.enqueue(Event(user_id="u1", value=1.0))
    await queue.enqueue(Event(user_id="u1", value=2.5))
    await asyncio.sleep(0.3)
    await queue.stop()

    assert len(received) == 1
    assert sum(e.value for e in received[0]) == pytest.approx(3.5)


@pytest.mark.asyncio
async def test_keys_independentes():
    """Conversas diferentes não interferem entre si."""
    received: dict[str, list[Message]] = {}

    async def on_flush(key: str, items: list[Message]) -> None:
        received[key] = items

    queue = DebouncedQueue(
        schema=Message,
        key_fn=lambda m: m.convo_id,
        on_flush=on_flush,
        backend=MemoryBackend(),
        delay=0.1,
        tick=0.05,
    )
    await queue.start()

    await queue.enqueue(Message(convo_id="c1", text="msg c1"))
    await queue.enqueue(Message(convo_id="c2", text="msg c2 parte 1"))
    await queue.enqueue(Message(convo_id="c2", text="msg c2 parte 2"))

    await asyncio.sleep(0.3)
    await queue.stop()

    assert "c1" in received
    assert "c2" in received
    assert len(received["c1"]) == 1
    assert len(received["c2"]) == 2


@pytest.mark.asyncio
async def test_flush_now_no_shutdown():
    """flush_now drena o buffer imediatamente."""
    received: list[tuple[str, list[Message]]] = []

    async def on_flush(key: str, items: list[Message]) -> None:
        received.append((key, items))

    backend = MemoryBackend()
    queue = DebouncedQueue(
        schema=Message,
        key_fn=lambda m: m.convo_id,
        on_flush=on_flush,
        backend=backend,
        delay=60.0,  # nunca expiraria naturalmente
        tick=60.0,
    )
    await queue.start()
    await queue.enqueue(Message(convo_id="c1", text="urgente"))

    # flush_now ignora o delay
    await queue.flush_now()

    assert len(received) == 1
    assert received[0][1][0].text == "urgente"

    await queue.stop()


@pytest.mark.asyncio
async def test_stop_drena_buffer():
    """stop() faz flush final antes de encerrar."""
    received: list[tuple[str, list[Message]]] = []

    async def on_flush(key: str, items: list[Message]) -> None:
        received.append((key, items))

    queue = DebouncedQueue(
        schema=Message,
        key_fn=lambda m: m.convo_id,
        on_flush=on_flush,
        backend=MemoryBackend(),
        delay=60.0,
        tick=60.0,
    )
    await queue.start()
    await queue.enqueue(Message(convo_id="c1", text="última mensagem"))

    # stop() deve fazer flush antes de sair
    await queue.stop()

    assert len(received) == 1
