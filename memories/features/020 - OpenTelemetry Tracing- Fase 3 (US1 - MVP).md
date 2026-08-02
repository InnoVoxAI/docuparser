---
title: '020 - OpenTelemetry Tracing: Fase 3 (US1 - MVP)'
type: note
permalink: docuparser/features/020-opentelemetry-tracing-fase-3-us1-mvp
tags:
- feature-020
- opentelemetry
- observability
---

## Status

Fase 3 (User Story 1 — trace de ponta a ponta) da feature `020-opentelemetry-tracing` implementada e testada (T029-T043). T044 (validação manual via quickstart.md com stack Docker completa + Jaeger UI) **fica pendente** — não executável no ambiente desta sessão (sem Zeebe/MinIO/Redis reais rodando).

## O que mudou

- **Consumidores de evento** (`extract_trace_link()` + `links=[...]`, research.md R4) — mesmo padrão de decorator em 4 arquivos, cada um com sua própria cópia local de `_traced_consumer(span_name)` (não há módulo compartilhado de decorator entre serviços, cada serviço só importa `docuparse_events`/`docuparse_observability`):
  - `backend-core/documents/services/event_consumers.py`: decorator aplicado a `consume_document_received`, `consume_extraction_completed`, `consume_ocr_completed`, `consume_ocr_failed`, `consume_erp_sent`, `consume_erp_failed`. Nome do span = `"{event_type} process"`.
  - `backend-ocr/application/ocr_event_worker.py`: `handle_document_received_event`.
  - `layout-service/application/layout_event_worker.py`: `handle_ocr_completed_event`.
  - `langextract-service/application/extraction_event_worker.py`: `handle_layout_classified_event`.
- **Zeebe/BPMN** (Span Links, não parent-child — research.md R3):
  - `camunda-workers/scripts/start_process.py`: `opentelemetry.propagate.inject(variables)` injeta `traceparent` direto no dict `variables` do processo (ao lado de `correlationId`), antes de `client.run_process()`.
  - `camunda-workers/src/workers/_tracing.py` (novo): `extract_trace_link_from_job(job_variables: dict) -> Link | None` (lê `traceparent`/`tracestate` de um dict plano de variáveis) + decorator `traced_job(job_type)` que inicia `zeebe.job.{job_type}` com o link.
  - Decorator `@traced_job(...)` aplicado nos 9 task handlers em `document.py`, `ocr.py`, `layout.py`, `extraction.py`, `validation.py`, `erp.py` — **sempre entre** `@router.task(...)` e `async def`, nessa ordem (`.task()` por cima, `traced_job` por baixo), porque decorators aplicam bottom-up e o pyzeebe precisa introspectar a assinatura *original* da função via `inspect.signature()` seguindo `__wrapped__` (setado por `functools.wraps`) para decidir `variables_to_fetch`.
  - **Achado importante sobre pyzeebe**: `ZeebeTaskRouter.task()` decide quais variáveis buscar do Zeebe via `pyzeebe.function_tools.parameter_tools.get_parameters_from_function()`, que inspeciona a assinatura da função decorada. Se a função tem `**kwargs` (todos os 9 handlers existentes já tinham, antes desta feature), `variables_to_fetch=[]`, que pyzeebe interpreta como "busca *todas* as variáveis do job" — por isso `traceparent` (adicionado em `start_process.py`) chega automaticamente em `**kwargs` de cada handler, sem precisar declarar o parâmetro explicitamente nem usar o parâmetro especial anotado `pyzeebe.Job`. Verificado empiricamente com `task.config.variables_to_fetch == []` e uma chamada real (mockando `core_client`) confirmando span `zeebe.job.docuparse-register-document` com link para o trace_id do `traceparent` injetado.

## Bug encontrado e corrigido (não estava nos tasks originais, mas quebra US1 em produção)

`EventBus.publish()` (`LocalJsonlEventBus`/`RedisStreamEventBus` em `shared/docuparse_events/__init__.py`) chamava `event = inject_trace_context(event)`, e `inject_trace_context` **criava um dict novo** (`{**event, "trace_context": carrier}`) em vez de mutar o dict recebido. Isso é invisível sem span ativo (T030 passa), mas assim que um span real está ativo ao redor do consumidor (exatamente o que esta fase faz), os `*_event_worker.py` que fazem `publisher.publish(stream, event_dict); return event_dict` retornam um dict **sem** `trace_context`, enquanto o que foi de fato persistido no stream **tem** `trace_context` — os dois divergem. Descoberto porque `test_document_received_becomes_ocr_completed`/`test_document_received_failure_publishes_ocr_failed` (backend-ocr) só falham quando rodados na mesma sessão pytest que primeiro importa `api/app.py` (que chama `configure_tracing`, promovendo o `TracerProvider` global de No-Op pra real) — passavam isolados, por isso não pegava em execução arquivo-a-arquivo.

**Fix**: `inject_trace_context()` agora muta `event["trace_context"] = carrier` in-place (além de retornar), então qualquer caller que guarda a mesma referência de dict (o padrão universal em `*_event_worker.py`) enxerga o valor efetivamente publicado. Sem efeito colateral novo — todos os callers de `publish()` no repo já descartavam o retorno (`int | str`, offset/id) e não dependiam de imutabilidade do dict passado.

## Verificação

Ambiente local sem Docker Compose completo — Postgres local via `docker compose up -d postgres` (único serviço necessário para os testes Django com `django_tenants`, que exige schema real e não funciona com o fallback SQLite). `.venv` criadas via `uv venv` para `layout-service` e `camunda-workers` (não existiam antes desta sessão).

- `shared`: 42/42 (`test_docuparse_events_tracing.py` novo: 4/4).
- `backend-core`: 184/184 (excluindo `test_e2e_local_pipeline.py`, que já falha na coleta por bug pré-existente e não relacionado — `backend-com/src/backend_com/config.py` não existe, só `backend-com/config.py` top-level; `__init__.py` do pacote também ausente, só sobra `__pycache__`, indício de arquivos apagados fora do histórico do git). `test_tracing_propagation.py` novo (T029): sobe um `ThreadingHTTPServer` local fingindo `backend-ocr`, confirma `traceparent` recebido bate com o trace_id do span pai e que o span de saída (`RequestsInstrumentor`, automático) tem o `parent` correto — **nenhuma mudança de código em `ocr_client.py`**, só verificação de infraestrutura já existente da Fase 2.
- `backend-ocr`: 14/24 (10 falhas pré-existentes por fixtures PDF ausentes, confirmadas idênticas antes/depois via stash pontual do arquivo).
- `layout-service`: 6/6. `langextract-service`: 6/6.
- `camunda-workers`: 2/2 (`test_tracing.py` novo, T031) + smoke test manual confirmando decorator/pyzeebe interação (ver achado acima).

## Próximos passos

Fase 4 (US2 — gargalos de performance, majoritariamente auditoria/validação de naming, T045-T047), Fase 5 (US3 — falhas de comunicação, T048-T052), Fase 6 (US4 — captura de exceção, T053-T061), Fase 7 (Polish — tail sampling, benchmark, T062-T068).

T044 (validação manual E2E no Jaeger com o caminho assíncrono/Zeebe completo) segue pendente — precisa do `docker compose up` completo com os profiles `async-workers`/`camunda` (ver quickstart.md).

Ver [[../../docs/specs/020-opentelemetry-tracing/tasks.md|tasks.md]]. Ver também [[020 - OpenTelemetry Tracing- Fase 2 (Foundational)]].
