---
title: USE_TELEMETRY torna OpenTelemetry opcional
type: decision
permalink: docuparser/decisions/use-telemetry-torna-open-telemetry-opcional
tags:
- opentelemetry
- tracing
- configuracao
---

## Contexto

O tracing OpenTelemetry (feature 020, ver `docs/specs/020-opentelemetry-tracing/plan.md`) foi implementado e roda em todos os backends (`backend-com`, `backend-core`, `backend-ocr`, `layout-service`, `langextract-service`, `camunda-workers`), mas o Collector (`otel-collector`) ainda não está instalado nos servidores de produção do usuário. Sem isso, cada boot tentava exportar spans para um endpoint inalcançável.

## Decisão

Adicionada a env var `USE_TELEMETRY` (default `false`) que liga/desliga tracing globalmente:

- `shared/docuparse_observability/tracing.py::is_telemetry_enabled()` — lê `USE_TELEMETRY` (`1`/`true`/`yes`/`on` = ligado, qualquer outro valor ou ausência = desligado).
- `configure_tracing()` vira no-op quando desligado — não cria `TracerProvider`/`OTLPSpanExporter`, mantém o `ProxyTracerProvider` default (no-op) da API do OpenTelemetry. Nenhum outro código precisa mudar: `trace.get_tracer(...)` em qualquer lugar (`processing_queue.py`, `event_consumers.py`, `ocr_processor.py`, `camunda-workers/src/workers/_tracing.py`) continua funcionando sem erro, só não exporta nada.
- Cada `api/app.py`/`settings.py` que chama `XInstrumentor().instrument()` (Django, Requests, Redis, HTTPX, gRPC, FastAPI) agora guarda essas chamadas atrás do mesmo `is_telemetry_enabled()`, para não instrumentar bibliotecas à toa quando telemetry está off.
- `docker-compose.yml` (ambiente de dev local, que sobe o `otel-collector` junto) seta `USE_TELEMETRY: ${USE_TELEMETRY:-true}` nos 6 serviços de backend — dev continua com tracing ligado por padrão.
- `.env` local (raiz do repo, gitignored) ganhou `USE_TELEMETRY=true` pelo mesmo motivo — sem isso o teste `backend-core/documents/tests/test_tracing_resilience.py` quebraria (ele assume um `TracerProvider` de verdade registrado para poder anexar um `SpanProcessor` extra).

## Por quê

Usuário quer poder rodar os backends em produção sem o Collector instalado, sem falhas/latência de export nem necessidade de tocar em cada serviço individualmente — flag única, default seguro (desligado).

## Como aplicar

- Em servidores sem Collector: não setar `USE_TELEMETRY` (ou setar `false`) — comportamento já é seguro por padrão.
- Ao instalar o Collector num servidor, só setar `USE_TELEMETRY=true` (+ `OTEL_EXPORTER_OTLP_ENDPOINT` apontando pro Collector real) — nenhuma mudança de código necessária.
- Novo serviço que exporte tracing deve seguir o mesmo padrão: chamar `configure_tracing()` incondicionalmente (ela já checa a flag) e guardar `XInstrumentor().instrument()` atrás de `is_telemetry_enabled()`.
