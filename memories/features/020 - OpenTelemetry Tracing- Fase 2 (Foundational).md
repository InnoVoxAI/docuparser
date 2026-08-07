---
title: '020 - OpenTelemetry Tracing: Fase 2 (Foundational)'
type: note
permalink: docuparser/features/020-opentelemetry-tracing-fase-2-foundational
tags:
- feature-020
- opentelemetry
- observability
---

## Status

Fase 2 (Foundational) da feature `020-opentelemetry-tracing` implementada (T014-T028). Todo processo agora chama `configure_tracing()` no bootstrap e emite spans para HTTP síncrono/Redis; eventos carregam `trace_context`; redação central ativa. Fases de história de usuário (US1-US4, T029+) ainda **não** implementadas.

## O que mudou

- `docuparse-project/shared/docuparse_observability/tracing.py` (novo): `configure_tracing(service_name)` — `TracerProvider` com `Resource` (`service.name` via `OTEL_SERVICE_NAME` env, fallback pro argumento; `service.version` via `OTEL_SERVICE_VERSION`, default `0.0.0`; `deployment.environment` via `DEPLOYMENT_ENVIRONMENT`), `OTLPSpanExporter` (grpc, timeout 2s) + `BatchSpanProcessor`, idempotente por `service_name` (guard em `set` de módulo — evita exporters/threads duplicados em reimport/teste). `RedactingSpanProcessor` registrado *antes* do `BatchSpanProcessor` (ordem importa: precisa rodar antes da exportação) — remove atributos da denylist (`http.request.body`, `http.response.body`, `authorization`, sufixos `_token`/`_secret`/`_password`, case-insensitive) substituindo `span._attributes` inteiro (única forma suportada de mutar um `ReadableSpan` — `BoundedAttributes.__setitem__` lança `TypeError`, confirmado empiricamente).
- `docuparse-project/shared/docuparse_observability/__init__.py`: `log_event()` agora inclui `trace_id`/`span_id` (hex, do span ativo via `trace.get_current_span()`) quando existir um — R8.
- `docuparse-project/shared/docuparse_events/__init__.py`: `inject_trace_context(event)` (chamado no início de `LocalJsonlEventBus.publish()`/`RedisStreamEventBus.publish()`) e `extract_trace_link(event) -> Link | None` (usa `opentelemetry.propagate.inject/extract`). Sem span ativo, `trace_context` fica como já estava (tipicamente `None`) — não força um valor vazio.
- Bootstrap por serviço (`configure_tracing()` + instrumentors correspondentes, ver `contracts/tracing-conventions.md`):
  - `backend-com/api/app.py`, `backend-ocr/api/app.py`, `langextract-service/api/app.py`, `layout-service/api/app.py`: chamada antes de `FastAPI(...)`, seguida de `FastAPIInstrumentor.instrument_app(app)` logo após a criação do app.
  - `backend-core/core/settings.py`: chamada **no fim do próprio `settings.py`** (não em `wsgi.py`) — decisão deliberada: `settings.py` é importado por todo entrypoint Django (`runserver`, `manage.py migrate/consume_events/seed_data`, testes), enquanto `wsgi.py` só roda para serving HTTP. `DjangoInstrumentor().instrument()` funciona correndo de dentro do próprio módulo settings (mutando `MIDDLEWARE` já definido acima no arquivo) — verificado empiricamente que o self-import circular do Django resolve corretamente (o módulo já está parcialmente populado em `sys.modules` quando `django.conf.settings` tenta reimportá-lo). Isso também instrumenta o comando `consume_events` (consumidor Redis), necessário para T032 (Fase 3).
  - `camunda-workers/src/main.py`: chamada + `HTTPXClientInstrumentor`/`GrpcInstrumentorClient`.
- CORS: `backend-com` (`CORSMiddleware.allow_headers`) e `backend-core` (`CORS_ALLOW_HEADERS = [*corsheaders.defaults.default_headers, "traceparent", "tracestate"]`) liberam `traceparent`/`tracestate` — R9.
- `docuparse-project/frontend/src/shared/lib/tracing.ts` (novo): `WebTracerProvider` (API v2 — `resourceFromAttributes()`, não `new Resource()`; `spanProcessors` no construtor) + `BatchSpanProcessor(OTLPTraceExporter({ url }))`, `provider.register({ contextManager: new ZoneContextManager(), propagator: new W3CTraceContextPropagator() })`, `registerInstrumentations` com `FetchInstrumentation`/`XMLHttpRequestInstrumentation` (ambas com `propagateTraceHeaderCorsUrls` derivado de `VITE_BACKEND_CORE_URL`/`VITE_BACKEND_COM_URL` — vazio em dev, same-origin via proxy Vite). Endpoint OTLP HTTP via novo env `VITE_OTEL_EXPORTER_OTLP_ENDPOINT` (default `http://localhost:4318/v1/traces`, casa com a porta `4318:4318` já exposta pelo `otel-collector` no compose). Chamada em `frontend/src/app/main.tsx` (entrypoint real — o `main.tsx` citado no `plan.md`/`tasks.md` vive em `src/app/`, não em `src/`), antes de qualquer render/chamada de API.

## Desvio de infraestrutura não coberto pela task original (necessário para T024)

`camunda-workers` não tinha nenhuma forma de importar `shared/docuparse_observability` — `Dockerfile` copiava só `src/`, `PYTHONPATH=/app/src`, e o `docker-compose.yml` usava `build.context: ./camunda-workers` (não alcança `../shared`) sem montar `/shared`/`/contracts`. Corrigido para espelhar o padrão de `backend-core`/`backend-ocr`:
- `camunda-workers/Dockerfile`: `context` agora é a raiz do repo (mudança correspondente em `docker-compose.yml`: `build.context: .`, `dockerfile: camunda-workers/Dockerfile`); copia `shared/` → `/shared`, `contracts/` → `/contracts`; `PYTHONPATH=/app/src:/contracts:/shared`.
- `docker-compose.yml` (serviço `camunda-workers`): + volumes `./contracts:/contracts:ro`, `./shared:/shared:ro`; + env `PYTHONPATH: /app/src:/contracts:/shared`.

## Verificação

Sem Postgres/docker-compose local disponível neste ambiente, validação feita via `uv sync`/`pip install` + smoke imports + suites de teste existentes por serviço:
- `backend-com`: `uv sync` OK, `import api.app` OK. Suite de testes não roda neste ambiente (bug pré-existente e não relacionado: `starlette==1.3.1` pede pacote inexistente `httpx2` — sem diff em `uv.lock`/`pyproject.toml`, confirmado pré-existente).
- `backend-core`: `uv sync` OK; `django.setup()` + checagem direta confirmam `MIDDLEWARE` contém o middleware OTel e `CORS_ALLOW_HEADERS` contém `traceparent`. Suite de testes majoritariamente não roda neste ambiente (todas as 280 falhas são `AttributeError: 'DatabaseWrapper' object has no attribute 'set_schema'` — `django_tenants` exige PostgreSQL real, ambiente local usa fallback SQLite; pré-existente, não relacionado a tracing). `inject_trace_context`/`extract_trace_link`/`log_event` validados via scripts diretos usando as dependências reais instaladas (ver seção abaixo).
- `backend-ocr`: `uv sync` OK, import OK, 14/24 testes passam (10 falhas pré-existentes por fixtures de PDF ausentes no ambiente, ex. `docs_teste/*.pdf` inexistente). Comportamento fail-open (R6) observado na prática: exporter tentou `otel-collector:4317` (inalcançável), logou `StatusCode.UNAVAILABLE` e retry, mas a suite completou normalmente sem travar/erro.
- `langextract-service`: `uv sync` OK, import OK, 6/6 testes passam.
- `layout-service`: `pip install -r requirements.txt` OK, import OK, 6/6 testes passam.
- `camunda-workers`: `pip install -r requirements.txt` OK, `import main` OK (confirma que o fix de Dockerfile/PYTHONPATH resolve `docuparse_observability` corretamente).
- `RedactingSpanProcessor` verificado ponta a ponta com um exportador de captura: `Authorization`/`api_token`/`user_password`/`http.request.body` removidos, `http.method`/`tenant_id` preservados.
- Frontend: `npm install --legacy-peer-deps` (já era o padrão do CI), `npm run typecheck` limpo, `npm run lint` sem erros novos (só warnings pré-existentes de `exhaustive-deps` em arquivos não tocados), `npm run test:run` com as mesmas 18 falhas pré-existentes (erro de `AbortSignal` do MSW em `flows.test.tsx`) confirmadas via `git stash` do meu diff — falham igual sem minhas mudanças.
- `docker compose config -q` sem erros após as mudanças de `camunda-workers`.

## Próximos passos

Fase 3 (US1 — MVP, T029-T044): testes de propagação (Core↔OCR via `InMemorySpanExporter`, eventos, job Zeebe), `extract_trace_link()` aplicado nos consumidores de evento e workers Zeebe, serialização de `traceparent` como variável de processo Zeebe (T036) + helper `extract_trace_link_from_job()` (T037, novo `camunda-workers/src/workers/_tracing.py`).

Ver [[../../docs/specs/020-opentelemetry-tracing/tasks.md|tasks.md]] para o detalhamento completo. Ver também [[020 - OpenTelemetry Tracing- Fase 1 (Setup)]].
