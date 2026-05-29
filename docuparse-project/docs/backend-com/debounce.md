# Debounce / DebouncedQueue - Backend Com

Este documento descreve a fila com debounce usada no backend-com, incluindo backends, regras de flush e integracao.

## Visao geral do modulo

Arquivo principal:
- src/atoms/debounce/debounced_queue.py

O DebouncedQueue e um orquestrador generico que:
- Agrupa eventos por chave (ex: conversation_id).
- Espera um periodo de silencio (delay) antes de executar o handler.
- Pode forcar flush por max_wait.
- Suporta backends plugaveis (Memory, Postgres, Celery).

## Conceitos e regras

- delay: tempo minimo sem novos eventos para flush.
- max_wait: tempo maximo que um grupo pode ficar acumulando (evita starvation).
- tick: intervalo do loop de polling (apenas em backends pull-based).
- on_flush: callback async que recebe (key, items).
- on_error: callback async que recebe (key, items, exc) quando on_flush falha.

## Backends suportados

### MemoryBackend
- Estado em memoria.
- Indicado para testes e dev local.
- Nao serve para multi-worker.

### PostgresBackend
- Armazena itens em tabela debounced_queue.
- UPSERT com JSONB e SKIP LOCKED.
- Pull-based: DebouncedQueue chama flush_ready periodicamente.

SQL usado:
- SETUP_SQL cria tabela e indices.
- PUSH_SQL realiza UPSERT e acumula items.
- FLUSH_SQL busca e remove grupos prontos (delay ou max_wait).

### CeleryBackend
- Redis + Celery.
- Push-based: cada push agenda uma task Celery.
- Usa guard de timestamp para evitar flushes obsoletos.
- Requer register_tasks() em modulo importado pelo worker.

## Fluxo interno do DebouncedQueue

1. enqueue() serializa item (BaseModel ou dataclass) e chama backend.push().
2. No modo pull-based, o loop chama backend.flush_ready() a cada tick.
3. Cada grupo pronto e deserializado e enviado ao on_flush.
4. Em erro, on_error e chamado (se configurado).

## Dependencias

Principais dependencias:
- pydantic (para BaseModel)
- asyncpg (para PostgresBackend)
- redis + celery (para CeleryBackend)

## Exemplos e testes

- src/atoms/debounce/example.py
  - Exemplo de WhatsApp + DebouncedQueue + PostgresBackend.
- src/atoms/debounce/pytest.py
  - Testes com MemoryBackend e max_wait.
- src/atoms/debounce/celery_guide.md
  - Guia completo para integrar com Celery.

## Pontos de integracao

O DebouncedQueue e um utilitario generico. A integracao tipica e:
- Webhook recebe eventos e chama queue.enqueue().
- on_flush agrega e chama o handler principal (LLM, API externa, etc).
