---
title: '020 - OpenTelemetry Tracing: Fase 1 (Setup)'
type: note
permalink: docuparser/features/020-opentelemetry-tracing-fase-1-setup
tags:
- feature-020
- opentelemetry
- observability
---

## Status

Fase 1 (Setup) da feature `020-opentelemetry-tracing` implementada (T001-T013). Fase 2 (Foundational — bootstrap central `configure_tracing()`, redação em processo, injeção/extração de `trace_context`, CORS) e as fases de histórias de usuário (US1-US4) ainda **não** implementadas.

## O que mudou

- `.specify/memory/constitution.md`: amendment MINOR (1.0.0 → 1.1.0), nova entrada em "Technology Standards" para "OpenTelemetry Collector + Jaeger (rastreamento distribuído)" como infraestrutura aditiva (research.md R11).
- `docuparse-project/otel-collector-config.yaml` (novo): receivers OTLP gRPC (4317)/HTTP (4318), processor `redaction` (deny-by-default, allowlist de `data-model.md` — defesa em profundidade, complementar ao `SpanProcessor` em processo que será feito em T014/T015), exporter `otlp/jaeger` para `jaeger:4317`. *Tail sampling* (T062) ainda não incluído — fica para a fase Polish.
- `docuparse-project/docker-compose.yml`: novos serviços `otel-collector` (`otel/opentelemetry-collector-contrib:0.157.0`, monta o config acima) e `jaeger` (`jaegertracing/all-in-one:1.76.0`, `COLLECTOR_OTLP_ENABLED=true`, UI em `16686`). Env vars `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317`, `DEPLOYMENT_ENVIRONMENT` adicionadas aos 7 serviços de aplicação listados na task (`backend-com`, `backend-core`, `backend-ocr`, `langextract-service`, `layout-service`, `camunda-workers`, `frontend`) — **não** adicionadas aos serviços `*-worker`/`*-events` (não estavam na lista literal de T005).
- `docuparse-project/contracts/events/schemas.py`: campo `trace_context: dict[str, str] | None = None` no `BaseEvent`, ao lado de `correlation_id`.
- Dependências OTel adicionadas e `uv lock` regenerado (resolveu sem conflitos) em `backend-com`, `backend-core`, `backend-ocr`, `langextract-service` (`pyproject.toml` + `uv.lock`); adicionadas em formato `requirements.txt` pinado (`==`) em `layout-service` e `camunda-workers`; adicionadas em `frontend/package.json` (sem lockfile commitado, nada a regenerar).
- Versões usadas (consultadas via PyPI/npm/Docker Hub no momento da implementação, 2026-08-02): `opentelemetry-sdk`/`opentelemetry-exporter-otlp-proto-grpc` `1.44.0`; instrumentation packages Python `0.65b0`; `@opentelemetry/sdk-trace-web`/`@opentelemetry/context-zone` `^2.10.0`; `@opentelemetry/instrumentation-fetch`/`instrumentation-xml-http-request`/`exporter-trace-otlp-http` `^0.221.0`.

## Decisão de implementação não coberta pela task original

O `otel-collector-config.yaml` (T002) pede "processor de redação básico (ver T014)". T014 é o `SpanProcessor` em processo (Python, fase Foundational) — o processor `redaction` do Collector adicionado aqui é uma camada **adicional** no Collector, não uma antecipação de T014/T015. Optei por `allow_all_keys: false` + `allowed_keys` (allowlist de `data-model.md`) em vez de tentar montar uma denylist por regex (`*_token`/`*_secret`/`*_password`) porque o processor `redaction` do collector-contrib não suporta bem padrões de sufixo de chave — negar por padrão e permitir só o allowlist cobre a denylist automaticamente, sem enumerá-la.

## Verificação

- `docker compose config -q` sem erros (`docuparse-project/docker-compose.yml` válido).
- YAML do `otel-collector-config.yaml` validado com `ruby -ryaml`.
- TOML dos 4 `pyproject.toml` editados validado com `tomllib`; `package.json` validado com `json.load`.
- `uv lock` rodado em `backend-com`, `backend-core`, `backend-ocr`, `langextract-service` — resolveu sem conflitos, nenhum pacote existente rebaixado.

## Próximos passos

Fase 2 (Foundational, T014-T028): `configure_tracing()` em `shared/docuparse_observability/tracing.py`, `SpanProcessor` de redação em processo, extensão de `log_event()`, injeção/extração de `trace_context` em `shared/docuparse_events`, bootstrap por serviço, CORS para `traceparent`/`tracestate`, bootstrap do SDK Web no frontend.

Ver [[../../docs/specs/020-opentelemetry-tracing/tasks.md|tasks.md]] para o detalhamento completo.
