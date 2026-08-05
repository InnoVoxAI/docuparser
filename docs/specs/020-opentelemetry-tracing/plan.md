# Implementation Plan: Rastreamento Distribuído (OpenTelemetry) entre Serviços

**Branch**: `016-opentelemetry-tracing` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `docs/specs/020-opentelemetry-tracing/spec.md`

## Summary

Instrumentar os seis processos de runtime do sistema — `backend-com`, `backend-core`, `backend-ocr`, `langextract-service`, `layout-service` (FastAPI/Django) e `camunda-workers` (worker Zeebe) — mais o `frontend` (React/Vite), com OpenTelemetry, propagando um único contexto de trace através de chamadas HTTP síncronas (W3C Trace Context), do barramento de eventos assíncrono (Redis Streams, via novo campo `trace_context` no schema de evento compartilhado) e da orquestração BPMN/Zeebe (via variável de processo + Span Links). O bootstrap de tracing é centralizado num novo módulo `shared/docuparse_observability/tracing.py`, reaproveitando o pacote já compartilhado via `PYTHONPATH` por todos os serviços Python (mesmo padrão de `docuparse_events`/`docuparse_storage`). Um novo par de serviços (`otel-collector` + `jaeger`) é adicionado ao `docker-compose.yml` como backend de coleta/visualização, com *tail sampling* no Collector para garantir 100% de retenção de traces com erro (FR-009/SC-006) mesmo sob amostragem reduzida, e exportação sempre não-bloqueante para nunca degradar requisições de usuário quando o Collector estiver indisponível (FR-008). Um processor central de redação garante que nenhum atributo de span contenha conteúdo de documento, dado pessoal ou credenciais (FR-006). A introdução dessa nova infraestrutura de observabilidade requer uma pequena emenda (MINOR) à `Constitution` (ver Constitution Check abaixo), já que "Technology Standards" hoje não lista nenhuma stack de tracing.

## Technical Context

**Language/Version**: Python 3.13 (`backend-com`, `backend-core`, `backend-ocr`, `langextract-service`, `layout-service`) / Python 3.12 (`camunda-workers`, versão distinta pré-existente — ver research.md R12) / TypeScript + React 19 (frontend, Node 22 em CI / Node 18 no Dockerfile — divergência pré-existente, não corrigida nesta feature)

**Primary Dependencies**: `opentelemetry-sdk`, `opentelemetry-exporter-otlp` + `opentelemetry-instrumentation-{fastapi,django,requests,httpx,redis,grpc}` (Python, conforme o serviço — ver research.md R2); `@opentelemetry/sdk-trace-web` + `@opentelemetry/instrumentation-{fetch,xml-http-request}` + `@opentelemetry/exporter-trace-otlp-http` (frontend); `otel/opentelemetry-collector-contrib` + `jaegertracing/all-in-one` (nova infraestrutura, containers)

**Storage**: N/A para dados de negócio (nenhuma tabela nova em PostgreSQL); traces armazenados no Jaeger (backend próprio do Jaeger all-in-one, volume Docker); único schema persistente afetado é o campo novo `trace_context` em `contracts/events/schemas.py` (payload de evento, não tabela)

**Testing**: pytest (todos os serviços Python, via `run_script.sh` por serviço, conforme CLAUDE.md), usando `opentelemetry.sdk.trace.export.InMemorySpanExporter` para testes de propagação sem depender de Collector/Jaeger reais; Vitest (frontend) para o bootstrap do SDK Web; teste de integração dedicado para o salto `backend-core ↔ backend-ocr` (já exigido pela Constitution, agora estendido para cobrir também a propagação de `traceparent`)

**Target Platform**: Linux containers via Docker Compose (dev/local, todos os 6 serviços + novo `otel-collector`/`jaeger`); `backend-core`, `backend-com`, `backend-ocr`, `langextract-service` também rodam em k8s via CI/CD (`.github/workflows/ci.yaml`) — `layout-service` e `camunda-workers` hoje só existem no docker-compose (sem job de deploy k8s ainda, gap pré-existente, ver research.md R12)

**Project Type**: Sistema distribuído multi-serviço (mudança transversal de infraestrutura/observabilidade, não uma feature de produto isolada) — toca os seis backends, o frontend, e os pacotes compartilhados (`contracts`, `shared`)

**Performance Goals**: Overhead de instrumentação ≤5% de latência adicional nas operações monitoradas (SC-004); manter os orçamentos já vigentes na Constitution (`backend-core` 200ms p95 não-processamento, `backend-ocr` 30s p95 processamento)

**Constraints**: Exportação de spans NUNCA pode bloquear ou falhar uma requisição de usuário quando o Collector está indisponível (FR-008, `BatchSpanProcessor` fail-open — research.md R6); nenhum atributo de span pode conter conteúdo de documento/dado pessoal/credencial (FR-006, processor de redação — research.md R7); 100% dos traces com erro devem ser retidos mesmo sob amostragem reduzida (FR-009/SC-006, tail sampling no Collector — research.md R5)

**Scale/Scope**: 6 processos de runtime backend + 1 frontend + 2 pacotes compartilhados (`contracts`, `shared`) + `docker-compose.yml`; ambientes dev/staging/produção

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Code Quality** — PASS, com ação. O bootstrap de tracing é centralizado em um único módulo novo (`shared/docuparse_observability/tracing.py`), evitando duplicar lógica de setup em 6 serviços — mantém a mesma disciplina de "sem código morto"/funções pequenas já cobrada nos demais módulos de `shared/`. Nenhuma vulnerabilidade nova esperada; o processor de redação (FR-006) é, ao contrário, uma camada adicional de proteção contra vazamento de dado sensível em telemetria — alinhado ao princípio de segurança da Constitution ("Input from users and external APIs MUST be validated at system boundaries"), estendido aqui para saída de telemetria.
- **II. Testing Standards** — PASS, com ação. Esta feature É, por definição, uma mudança em "contratos de API entre serviços" (novos cabeçalhos `traceparent`/`tracestate` propagados, novo campo `trace_context` no schema de evento) — a Constitution já exige teste de integração para o par Backend Core ↔ Backend OCR; esse teste deve ser estendido (não substituído) para também afirmar a propagação do cabeçalho de trace. Testes novos de unidade cobrem: o processor de redação (nenhum atributo proibido escapa), o comportamento fail-open do exporter (mock de Collector indisponível não deve lançar exceção nem atrasar a resposta), e a extração/injeção de `trace_context` nos publishers/consumers de evento.
- **III. User Experience Consistency** — PASS. Nenhuma mudança de contrato de resposta de API voltada ao usuário final (o envelope `{ "data", "error", "meta" }` não é alterado); a única superfície nova voltada a operação é interna (Jaeger UI), não exposta a usuários finais do DocuParse.
- **IV. Performance Requirements** — PASS, com verificação obrigatória antes de mergear. SC-004 (≤5% overhead) precisa ser medido (não apenas assumido) contra os orçamentos já vigentes (200ms p95 `backend-core`, 30s p95 `backend-ocr`) — tarefa de benchmark antes/depois faz parte do plano de tarefas. `BatchSpanProcessor` (não-bloqueante) e tail sampling no Collector (não no caminho de request) foram escolhidos precisamente para minimizar esse risco (ver research.md R5/R6).
- **Technology Standards (gap identificado, não uma violação de princípio)** — A seção "Technology Standards" da Constitution não lista hoje nenhuma ferramenta de observabilidade/tracing, e exige amendment antes de qualquer desvio de stack. A introdução do OTel Collector + Jaeger é estritamente **aditiva** (nova infraestrutura de suporte, nenhuma substituição de Django/FastAPI/React/PostgreSQL/Docker já padronizados) — tratada como amendment **MINOR** à Constitution, a ser preparado junto com esta feature (ver research.md R11), não como violação a ser justificada em Complexity Tracking.

Nenhuma violação não justificada dos quatro Core Principles. O único ponto de atenção de governança (Technology Standards) é resolvido por amendment aditivo, não por exceção.

## Project Structure

### Documentation (this feature)

```text
docs/specs/020-opentelemetry-tracing/
├── plan.md                          # This file
├── research.md                      # Phase 0 output
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/                       # Phase 1 output
│   ├── tracing-conventions.md
│   └── event-schema-trace-context.md
├── checklists/
│   └── requirements.md
└── tasks.md                         # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
docuparse-project/
├── shared/
│   └── docuparse_observability/
│       ├── __init__.py              # log_event() estendido para anexar trace_id/span_id (research.md R8)
│       └── tracing.py               # NOVO: configure_tracing(service_name), SpanProcessor de redação
│                                     #   (research.md R7), BatchSpanProcessor fail-open (R6)
├── contracts/
│   └── events/
│       └── schemas.py               # + campo trace_context: dict[str, str] | None (data-model.md)
├── backend-com/
│   ├── pyproject.toml                # + deps opentelemetry-{sdk,exporter-otlp,instrumentation-fastapi,-requests}
│   └── api/app.py                    # chama configure_tracing("backend-com") no bootstrap
├── backend-core/
│   ├── pyproject.toml                # + deps opentelemetry-{sdk,exporter-otlp,instrumentation-django,-requests,-redis}
│   ├── core/settings.py              # chama configure_tracing("backend-core"); CORS_ALLOW_HEADERS
│   │                                  #   += traceparent, tracestate (research.md R9)
│   ├── documents/services/
│   │   ├── ocr_client.py             # nenhuma mudança de lógica — instrumentação automática via requests
│   │   └── langextract_client.py     # idem
│   ├── documents/services/event_consumers.py   # extrai trace_context do evento, Span Link (research.md R4)
│   └── documents/tests/
│       └── test_tracing_propagation.py         # NOVO: estende o teste de contrato Core↔OCR já exigido
├── backend-ocr/
│   ├── pyproject.toml
│   └── api/app.py                    # configure_tracing("backend-ocr")
│   └── application/ocr_event_worker.py         # publica trace_context ao emitir ocr.completed/failed
├── langextract-service/
│   ├── pyproject.toml
│   └── api/app.py                    # configure_tracing("langextract-service")
│   └── application/extraction_event_worker.py
├── layout-service/
│   ├── requirements.txt              # + mesmas deps OTel (formato requirements.txt, não uv/pyproject)
│   └── api/app.py                    # configure_tracing("layout-service")
│   └── application/layout_event_worker.py
├── camunda-workers/
│   ├── requirements.txt              # + opentelemetry-{sdk,exporter-otlp,instrumentation-httpx,-grpc}
│   ├── src/main.py                   # configure_tracing("camunda-workers")
│   ├── src/workers/_http.py          # instrumentação automática via httpx instrumentor
│   └── src/workers/*.py              # extrai trace context da variável de processo Zeebe, Span Link (R3)
├── frontend/
│   ├── package.json                  # + @opentelemetry/{sdk-trace-web,instrumentation-fetch,
│   │                                  #   instrumentation-xml-http-request,exporter-trace-otlp-http}
│   └── src/
│       ├── shared/lib/tracing.ts     # NOVO: bootstrap do SDK Web, propagateTraceHeaderCorsUrls
│       └── main.tsx                  # chama a inicialização de tracing.ts
└── docker-compose.yml                # + serviços otel-collector, jaeger; env vars OTEL_SERVICE_NAME,
                                       #   OTEL_EXPORTER_OTLP_ENDPOINT, DEPLOYMENT_ENVIRONMENT por serviço

.specify/memory/constitution.md       # amendment MINOR: nova entrada em "Technology Standards"
                                       #   (OpenTelemetry Collector + Jaeger para tracing distribuído)
```

**Structure Decision**: Mudança transversal sem novo serviço de produto — estende os seis processos de runtime existentes e os dois pacotes compartilhados (`contracts`, `shared`) já usados via `PYTHONPATH`, seguindo o mesmo padrão de reaproveitamento já estabelecido por `docuparse_events`/`docuparse_storage`. Nenhuma reestruturação de diretórios é necessária; todas as mudanças são aditivas dentro da árvore de cada serviço já existente.

## Complexity Tracking

> Nenhuma violação de Core Principle requer justificativa nesta seção — o único ponto de governança (gap em Technology Standards) é endereçado via amendment aditivo à Constitution, não via exceção.
