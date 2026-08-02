---

description: "Task list for feature 020-opentelemetry-tracing"
---

# Tasks: Rastreamento Distribuído (OpenTelemetry) entre Serviços

**Input**: Design documents from `docs/specs/020-opentelemetry-tracing/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/tracing-conventions.md](./contracts/tracing-conventions.md), [contracts/event-schema-trace-context.md](./contracts/event-schema-trace-context.md), [quickstart.md](./quickstart.md)

**Tests**: Esta feature altera o contrato entre serviços (novos cabeçalhos `traceparent`/`tracestate` propagados, novo campo `trace_context` no schema de evento) — a Constituição (Princípio II) já exige teste de integração para o par Backend Core ↔ Backend OCR e testes de regressão para qualquer defeito corrigido; por isso, como na feature 019, as tarefas de teste abaixo são **obrigatórias**, não opcionais.

**Organization**: Tarefas agrupadas por história de usuário (US1-US4, prioridades do spec.md). US1 e US2 são P1; US3 e US4 são P2. Boa parte do trabalho pesado (instalar SDKs, criar o bootstrap central, ligar instrumentação automática em cada serviço) vive nas fases Setup/Foundational, porque as quatro histórias de usuário observam a mesma telemetria de ângulos diferentes — cada fase de história adiciona o que falta para essa história específica (continuidade assíncrona para US1, comparação de duração para US2, status de erro em falhas de comunicação para US3, captura de exceção de aplicação para US4) e sua verificação/teste correspondente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefas incompletas)
- **[Story]**: US1, US2, US3 ou US4
- Caminhos de arquivo são relativos à raiz do repositório (`docuparse-project/` é o diretório dos serviços)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar dependências, infraestrutura de coleta e o novo campo de schema antes de qualquer código de instrumentação

- [X] T001 Propor amendment MINOR à `.specify/memory/constitution.md` (seção "Technology Standards"), adicionando uma entrada para "OpenTelemetry Collector + Jaeger (tracing distribuído)" como nova infraestrutura aditiva — conforme research.md R11
- [X] T002 [P] Criar `docuparse-project/otel-collector-config.yaml` com receivers OTLP (gRPC/HTTP), processor de redação básico (ver T014) e exporter para Jaeger
- [X] T003 [P] Adicionar serviço `otel-collector` (imagem `otel/opentelemetry-collector-contrib`, montando `otel-collector-config.yaml`) ao `docuparse-project/docker-compose.yml`
- [X] T004 [P] Adicionar serviço `jaeger` (imagem `jaegertracing/all-in-one`, porta UI 16686) ao `docuparse-project/docker-compose.yml`, recebendo do `otel-collector`
- [X] T005 Adicionar env vars `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT` (`http://otel-collector:4317`), `DEPLOYMENT_ENVIRONMENT` para cada serviço de aplicação (`backend-com`, `backend-core`, `backend-ocr`, `langextract-service`, `layout-service`, `camunda-workers`, `frontend`) em `docuparse-project/docker-compose.yml` (depende de T003)
- [X] T006 [P] Adicionar campo `trace_context: dict[str, str] | None = None` ao schema base de evento em `docuparse-project/contracts/events/schemas.py`, conforme contracts/event-schema-trace-context.md
- [X] T007 [P] Adicionar dependências `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-requests`, `opentelemetry-instrumentation-redis` em `docuparse-project/backend-com/pyproject.toml`
- [X] T008 [P] Adicionar dependências `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`, `opentelemetry-instrumentation-django`, `opentelemetry-instrumentation-requests`, `opentelemetry-instrumentation-redis` em `docuparse-project/backend-core/pyproject.toml`
- [X] T009 [P] Adicionar dependências `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-redis` em `docuparse-project/backend-ocr/pyproject.toml`
- [X] T010 [P] Adicionar dependências `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-httpx`, `opentelemetry-instrumentation-redis` em `docuparse-project/langextract-service/pyproject.toml`
- [X] T011 [P] Adicionar as mesmas dependências OTel (formato `requirements.txt`, não `pyproject.toml`) em `docuparse-project/layout-service/requirements.txt`
- [X] T012 [P] Adicionar dependências `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`, `opentelemetry-instrumentation-httpx`, `opentelemetry-instrumentation-grpc` em `docuparse-project/camunda-workers/requirements.txt`
- [X] T013 [P] Adicionar dependências `@opentelemetry/sdk-trace-web`, `@opentelemetry/instrumentation-fetch`, `@opentelemetry/instrumentation-xml-http-request`, `@opentelemetry/exporter-trace-otlp-http`, `@opentelemetry/context-zone` em `docuparse-project/frontend/package.json`

**Checkpoint**: Infraestrutura de coleta/visualização no ar; todas as dependências declaradas; campo de schema pronto para uso.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Construir o bootstrap central de tracing e ligá-lo em cada processo — nenhuma história de usuário produz dado de trace observável sem esta fase

**⚠️ CRITICAL**: Nenhuma história de usuário pode ser validada antes desta fase estar completa

- [ ] T014 Implementar `configure_tracing(service_name: str) -> None` em `docuparse-project/shared/docuparse_observability/tracing.py` (arquivo novo): cria `TracerProvider` com `Resource` (`service.name`, `service.version`, `deployment.environment` a partir de env vars), exporter OTLP com timeout curto (1-2s) e `BatchSpanProcessor` (fail-open, research.md R6) (depende de T005-T012)
- [ ] T015 Implementar `SpanProcessor` de redação de dados sensíveis em `docuparse-project/shared/docuparse_observability/tracing.py`, aplicando a allowlist/denylist de atributos definida em `data-model.md` (remove/mascara `http.request.body`, `http.response.body`, `Authorization`, chaves terminadas em `_token`/`_secret`/`_password`, conteúdo de documento) e registrá-lo no `TracerProvider` de T014 (depende de T014)
- [ ] T016 [P] Estender `log_event()` em `docuparse-project/shared/docuparse_observability/__init__.py` para incluir `trace_id`/`span_id` do span ativo (via `opentelemetry.trace.get_current_span()`), quando existir (research.md R8)
- [ ] T017 Implementar injeção de `trace_context` (via `opentelemetry.propagate.inject()`) dentro de `EventBus.publish()` em `docuparse-project/shared/docuparse_events/__init__.py`, para `LocalJsonlEventBus` e `RedisStreamEventBus` (depende de T006, T014)
- [ ] T018 Implementar `extract_trace_link(event) -> Link | None` em `docuparse-project/shared/docuparse_events/__init__.py`, extraindo `trace_context` (via `opentelemetry.propagate.extract()`) do evento consumido e retornando um `opentelemetry.trace.Link` para uso pelos consumidores (depende de T006, T014)
- [ ] T019 [P] Chamar `configure_tracing("backend-com")` no bootstrap de `docuparse-project/backend-com/api/app.py`, habilitando `FastAPIInstrumentor`/`RequestsInstrumentor` (depende de T007, T014, T015)
- [ ] T020 [P] Chamar `configure_tracing("backend-core")` no bootstrap de `docuparse-project/backend-core/core/settings.py` (ou `core/wsgi.py`), habilitando `DjangoInstrumentor`/`RequestsInstrumentor`/`RedisInstrumentor` (depende de T008, T014, T015)
- [ ] T021 [P] Chamar `configure_tracing("backend-ocr")` no bootstrap de `docuparse-project/backend-ocr/api/app.py`, habilitando `FastAPIInstrumentor`/`RedisInstrumentor` (depende de T009, T014, T015)
- [ ] T022 [P] Chamar `configure_tracing("langextract-service")` no bootstrap de `docuparse-project/langextract-service/api/app.py`, habilitando `FastAPIInstrumentor`/`HTTPXClientInstrumentor`/`RedisInstrumentor` (depende de T010, T014, T015)
- [ ] T023 [P] Chamar `configure_tracing("layout-service")` no bootstrap de `docuparse-project/layout-service/api/app.py`, habilitando `FastAPIInstrumentor`/`RedisInstrumentor` (depende de T011, T014, T015)
- [ ] T024 [P] Chamar `configure_tracing("camunda-workers")` no bootstrap de `docuparse-project/camunda-workers/src/main.py`, habilitando `HTTPXClientInstrumentor`/`GrpcInstrumentorClient` (depende de T012, T014, T015)
- [ ] T025 Atualizar CORS em `docuparse-project/backend-com/api/app.py` (`CORSMiddleware`) para permitir os cabeçalhos `traceparent`/`tracestate` (research.md R9) (depende de T019)
- [ ] T026 Atualizar CORS em `docuparse-project/backend-core/core/settings.py` (`CORS_ALLOW_HEADERS` ou middleware equivalente) para permitir `traceparent`/`tracestate` (depende de T020)
- [ ] T027 [P] Criar `docuparse-project/frontend/src/shared/lib/tracing.ts`: bootstrap do `WebTracerProvider`, `FetchInstrumentation`/`XMLHttpRequestInstrumentation`, exporter OTLP HTTP, `propagateTraceHeaderCorsUrls` apontando para os hosts de `backend-core`/`backend-com` (dev e prod) (depende de T013)
- [ ] T028 Chamar a inicialização de `tracing.ts` em `docuparse-project/frontend/src/main.tsx`, antes de qualquer chamada de API (depende de T027)

**Checkpoint**: Todo processo emite spans para chamadas HTTP síncronas e comandos Redis; eventos carregam `trace_context`; redação central ativa; base pronta para as histórias de usuário.

---

## Phase 3: User Story 1 - Acompanhar uma requisição de ponta a ponta entre serviços (Priority: P1) 🎯 MVP

**Goal**: Localizar, por um único identificador, o caminho completo (síncrono e assíncrono) que uma requisição percorreu entre frontend e os backends.

**Independent Test**: Disparar uma operação que atravesse ≥2 serviços (ex.: upload de documento) e confirmar que um identificador único aparece nos registros de cada serviço envolvido, permitindo reconstruir a sequência completa — incluindo a etapa que continua via workflow/fila depois da resposta HTTP original.

### Tests for User Story 1

- [ ] T029 [P] [US1] Teste de integração em `docuparse-project/backend-core/documents/tests/test_tracing_propagation.py` (arquivo novo, estende o teste de contrato Core↔OCR já exigido pela Constituição): usando `InMemorySpanExporter`, confirmar que uma chamada de `documents/services/ocr_client.py` para `backend-ocr` propaga `traceparent` e produz um span filho corretamente contextualizado
- [ ] T030 [P] [US1] Teste unitário em `docuparse-project/shared/tests/test_docuparse_events_tracing.py` (arquivo novo): publicar um evento via `EventBus.publish()` e confirmar que `trace_context` é populado (T017); consumir o evento e confirmar que `extract_trace_link()` (T018) retorna um `Link` válido apontando para o contexto original
- [ ] T031 [P] [US1] Teste unitário em `docuparse-project/camunda-workers/tests/workers/test_tracing.py` (arquivo novo): confirmar que o helper de extração de contexto de trace a partir de variáveis de job Zeebe (T034) retorna um `Link` válido quando a variável está presente, e `None` quando ausente

### Implementation for User Story 1

- [ ] T032 [US1] Usar `extract_trace_link()` (T018) para iniciar o span de processamento com `links=[...]` em `docuparse-project/backend-core/documents/services/event_consumers.py`, para cada handler de evento consumido
- [ ] T033 [P] [US1] Usar `extract_trace_link()` (T018) para iniciar o span de processamento com `links=[...]` em `docuparse-project/backend-ocr/application/ocr_event_worker.py`
- [ ] T034 [P] [US1] Usar `extract_trace_link()` (T018) para iniciar o span de processamento com `links=[...]` em `docuparse-project/layout-service/application/layout_event_worker.py`
- [ ] T035 [P] [US1] Usar `extract_trace_link()` (T018) para iniciar o span de processamento com `links=[...]` em `docuparse-project/langextract-service/application/extraction_event_worker.py`
- [ ] T036 [US1] Serializar o `traceparent` ativo (via `opentelemetry.propagate.inject()`) como variável adicional do processo Zeebe, ao lado de `correlationId`, no ponto onde uma instância de processo é criada (`scripts/start_process.py` ou client Zeebe equivalente acionado por `backend-core`) (depende de T014)
- [ ] T037 [US1] Criar helper `extract_trace_link_from_job(job) -> Link | None` em `docuparse-project/camunda-workers/src/workers/_tracing.py` (arquivo novo), extraindo a variável de trace do job Zeebe via `opentelemetry.propagate.extract()` (depende de T036)
- [ ] T038 [P] [US1] Aplicar o helper de T037 (span com `links=[...]`) em `docuparse-project/camunda-workers/src/workers/document.py`
- [ ] T039 [P] [US1] Aplicar o helper de T037 em `docuparse-project/camunda-workers/src/workers/ocr.py`
- [ ] T040 [P] [US1] Aplicar o helper de T037 em `docuparse-project/camunda-workers/src/workers/layout.py`
- [ ] T041 [P] [US1] Aplicar o helper de T037 em `docuparse-project/camunda-workers/src/workers/extraction.py`
- [ ] T042 [P] [US1] Aplicar o helper de T037 em `docuparse-project/camunda-workers/src/workers/validation.py`
- [ ] T043 [P] [US1] Aplicar o helper de T037 em `docuparse-project/camunda-workers/src/workers/erp.py`
- [ ] T044 [US1] Executar os passos 1-3 do `quickstart.md` manualmente para validar visibilidade do trace de ponta a ponta no Jaeger, incluindo o trecho assíncrono/Zeebe (depende de T032-T043)

**Checkpoint**: Um trace único é reconstruível do frontend até qualquer backend, incluindo os saltos assíncronos (fila de eventos e workflow Zeebe) — História 1 completa e testável isoladamente.

---

## Phase 4: User Story 2 - Identificar gargalos de performance (Priority: P1)

**Goal**: Ver o tempo gasto em cada etapa/serviço de uma requisição, individualizado e comparável.

**Independent Test**: Executar uma operação de ponta a ponta e confirmar que o tempo total e o tempo de cada etapa aparecem separadamente e são comparáveis entre si.

### Tests for User Story 2

- [ ] T045 [P] [US2] Estender `docuparse-project/backend-core/documents/tests/test_tracing_propagation.py` (T029) com uma asserção de que cada span capturado tem um atributo de duração maior que zero e que spans de serviços diferentes são individualmente distinguíveis (não agregados)

### Implementation for User Story 2

- [ ] T046 [US2] Auditar os nomes de span aplicados pela instrumentação automática em `backend-com`, `backend-core`, `backend-ocr`, `langextract-service`, `layout-service`, `camunda-workers` (T019-T024), confirmando que seguem o padrão de baixa cardinalidade `{METHOD} {route_template}`/`zeebe.job.{job_type}`/`redis.{command} {stream}` (contracts/tracing-conventions.md item 5), sem IDs interpolados no nome
- [ ] T047 [US2] Executar o passo 3 (História 2) do `quickstart.md` manualmente, confirmando no Jaeger que é possível comparar a duração de uma mesma etapa (ex.: `backend-core → langextract-service`) entre múltiplas execuções (depende de T044, T046)

**Checkpoint**: Durações por etapa são visíveis e comparáveis — Histórias 1 e 2 completas em conjunto.

---

## Phase 5: User Story 3 - Diagnosticar falhas de comunicação entre serviços (Priority: P2)

**Goal**: Quando uma chamada entre serviços falha, o registro indica claramente origem, destino e natureza da falha.

**Independent Test**: Forçar indisponibilidade temporária de um serviço chamado por outro e confirmar que o span da chamada aparece com status de erro, indicando origem/destino e tipo de falha.

### Tests for User Story 3

- [ ] T048 [P] [US3] Teste de integração em `docuparse-project/backend-core/documents/tests/test_tracing_failures.py` (arquivo novo): simular indisponibilidade de `backend-ocr` (mock/timeout) e confirmar que o span de saída de `documents/services/ocr_client.py` tem `status=ERROR`, `net.peer.name`/`http.route` identificando o destino, e `error.type` identificando a natureza (timeout/conexão recusada)
- [ ] T049 [P] [US3] Teste unitário em `docuparse-project/camunda-workers/tests/workers/test_http_failures.py` (arquivo novo): simular falha de um dos clients HTTP em `src/workers/_http.py` e confirmar span de erro com origem/destino corretos

### Implementation for User Story 3

- [ ] T050 [US3] Confirmar/ajustar que `RequestsInstrumentor` (backend-core, T020) marca `status=ERROR` com `net.peer.name` em falhas de `documents/services/ocr_client.py` e `documents/services/langextract_client.py` (nenhuma mudança de lógica de negócio, apenas configuração de instrumentação se o comportamento default não for suficiente)
- [ ] T051 [P] [US3] Confirmar/ajustar o mesmo comportamento para os quatro clients HTTP em `docuparse-project/camunda-workers/src/workers/_http.py` (`core_client`, `ocr_client`, `layout_client`, `langextract_client`)
- [ ] T052 [US3] Executar o passo 3 (História 3) do `quickstart.md` manualmente — `docker compose stop backend-ocr`, repetir a requisição, confirmar span de erro visível no Jaeger — e religar o serviço em seguida (depende de T048-T051)

**Checkpoint**: Falhas de comunicação entre serviços aparecem claramente diagnosticáveis — Histórias 1-3 completas em conjunto.

---

## Phase 6: User Story 4 - Rastrear erros de aplicação ao longo de uma requisição (Priority: P2)

**Goal**: Um erro de aplicação em qualquer serviço fica associado ao trace completo, com contexto suficiente para localizá-lo, sem dado sensível.

**Independent Test**: Forçar um erro de aplicação numa etapa intermediária de uma requisição de ponta a ponta e confirmar que o erro aparece associado ao trace, sem conteúdo de documento nos atributos.

### Tests for User Story 4

- [ ] T053 [P] [US4] Teste unitário em `docuparse-project/shared/tests/test_tracing_redaction.py` (arquivo novo): confirmar que o `SpanProcessor` de redação (T015) remove/mascara atributos da denylist (`http.request.body`, `Authorization`, chaves `_token`/`_secret`/`_password`, conteúdo simulando texto de documento) antes da exportação
- [ ] T054 [US4] Teste de integração em `docuparse-project/backend-core/documents/tests/test_tracing_errors.py` (arquivo novo): forçar uma exceção não tratada numa etapa intermediária do fluxo de documento e confirmar que o span correspondente tem `status=ERROR`, evento de exceção anexado (`span.record_exception`), e nenhum atributo com conteúdo de documento/dado pessoal

### Implementation for User Story 4

- [ ] T055 [P] [US4] Adicionar captura de exceção (`span.record_exception()` + `status=ERROR`) no handler de exceção global de `docuparse-project/backend-com/api/app.py`
- [ ] T056 [P] [US4] Adicionar captura de exceção equivalente no middleware/handler de exceção de `docuparse-project/backend-core/core/settings.py` (ou middleware novo dedicado)
- [ ] T057 [P] [US4] Estender o `@app.exception_handler(Exception)` existente em `docuparse-project/backend-ocr/api/app.py` para também chamar `span.record_exception()`
- [ ] T058 [P] [US4] Adicionar um `@app.exception_handler(Exception)` novo (hoje inexistente) com captura de exceção em `docuparse-project/langextract-service/api/app.py`
- [ ] T059 [P] [US4] Adicionar um `@app.exception_handler(Exception)` novo (hoje inexistente) com captura de exceção em `docuparse-project/layout-service/api/app.py`
- [ ] T060 [P] [US4] Estender o helper de T037 (`_tracing.py`) para chamar `span.record_exception()` + `status=ERROR` quando um job handler Zeebe falha, aplicado nos seis módulos de `docuparse-project/camunda-workers/src/workers/*.py` (T038-T043)
- [ ] T061 [US4] Executar os passos 3 (História 4) e 5 (verificação de dados sensíveis) do `quickstart.md` manualmente (depende de T053-T060)

**Checkpoint**: Erros de aplicação em qualquer serviço ficam correlacionados ao trace, sem vazamento de dado sensível — todas as quatro histórias de usuário completas e testáveis independentemente.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Garantias de produção (amostragem, resiliência, desempenho) que atravessam todas as histórias

- [ ] T062 [P] Implementar a política de *tail sampling* no `otel-collector-config.yaml` (T002): `tailsamplingprocessor` com regra "sempre reter se algum span tiver status de erro" + amostragem probabilística configurável para o restante (FR-009/SC-006, research.md R5)
- [ ] T063 [P] Confirmar que os novos containers `otel-collector`/`jaeger` respeitam o limite de 2GB RAM por container já definido na Constituição, ajustando `docuparse-project/docker-compose.yml` se necessário
- [ ] T064 Teste de resiliência em `docuparse-project/backend-core/documents/tests/test_tracing_resilience.py` (arquivo novo): com o exporter apontando para um endpoint inalcançável, confirmar que uma requisição completa normalmente, sem aumento perceptível de latência nem erro 5xx (FR-008)
- [ ] T065 [P] Executar benchmark comparando p95 de latência antes/depois da instrumentação em um endpoint não-processamento de `backend-core` e no endpoint de processamento de `backend-ocr`, confirmando overhead ≤5% (SC-004) frente aos orçamentos já vigentes na Constituição (200ms/30s p95); registrar o resultado em `docs/specs/020-opentelemetry-tracing/research.md`
- [ ] T066 [P] Atualizar `docuparse-project/docs/TECHNICAL.md` (ou documento de arquitetura equivalente) para mencionar a nova stack de observabilidade (OTel Collector + Jaeger) e o fluxo de propagação de trace
- [ ] T067 [P] Teste Vitest em `docuparse-project/frontend/src/shared/lib/tracing.test.ts` (arquivo novo): confirmar que uma chamada `fetch`/`axios` de teste inclui o cabeçalho `traceparent` na requisição de saída
- [ ] T068 Executar a validação completa do `quickstart.md` (passos 1-6) como aceite final da feature (depende de todas as tarefas anteriores)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: Depende da conclusão do Setup — BLOQUEIA todas as histórias de usuário
- **User Stories (Phase 3+)**: Todas dependem da conclusão da fase Foundational
  - US1 e US2 (ambas P1) podem prosseguir em paralelo entre si, mas US2 se apoia nos spans que US1 termina de conectar (nomeação/duração já vêm da instrumentação de Foundational, então US2 é majoritariamente auditoria/validação)
  - US3 e US4 (ambas P2) podem começar assim que Foundational estiver pronta, independentemente de US1/US2 estarem concluídas
- **Polish (Final Phase)**: Depende de todas as histórias de usuário desejadas estarem completas

### User Story Dependencies

- **User Story 1 (P1)**: Pode começar após Foundational — depende de T014-T028 (bootstrap + injeção/extração de `trace_context` + CORS)
- **User Story 2 (P1)**: Pode começar após Foundational — reaproveita a instrumentação de US1 (naming/duration já são automáticos); a maior parte do trabalho é auditoria e teste, não código novo
- **User Story 3 (P2)**: Pode começar após Foundational — não depende de US1/US2 estarem completas, mas se beneficia da mesma instrumentação de saída HTTP já ligada em Foundational
- **User Story 4 (P2)**: Pode começar após Foundational — usa o helper de job Zeebe criado em US1 (T037) apenas se US1 já estiver em andamento; caso contrário, pode implementar sua própria captura de exceção nos handlers HTTP (T055-T059) de forma totalmente independente

### Parallel Opportunities

- Todas as tarefas [P] do Setup (T002-T004, T006-T013) podem rodar em paralelo
- Dentro do Foundational, T019-T024 (bootstrap por serviço) podem rodar em paralelo entre si depois que T014/T015 estiverem prontos
- Dentro de US1, T033-T035 (event workers) e T038-T043 (camunda job handlers) podem rodar em paralelo entre si
- US3 e US4 podem ser trabalhadas em paralelo por pessoas diferentes assim que Foundational estiver pronta

---

## Parallel Example: User Story 1

```bash
# Depois que T032-T037 estiverem prontos, aplicar o helper de trace-link a todos os workers Zeebe em paralelo:
Task: "Aplicar o helper de T037 em camunda-workers/src/workers/document.py"
Task: "Aplicar o helper de T037 em camunda-workers/src/workers/ocr.py"
Task: "Aplicar o helper de T037 em camunda-workers/src/workers/layout.py"
Task: "Aplicar o helper de T037 em camunda-workers/src/workers/extraction.py"
Task: "Aplicar o helper de T037 em camunda-workers/src/workers/validation.py"
Task: "Aplicar o helper de T037 em camunda-workers/src/workers/erp.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 — ambas P1)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRÍTICO — bloqueia todas as histórias)
3. Completar Phase 3: User Story 1 (trace de ponta a ponta)
4. Completar Phase 4: User Story 2 (gargalos de performance)
5. **PARAR e VALIDAR**: rodar `quickstart.md` passos 1-3 e confirmar valor entregue
6. Demonstrar/avaliar antes de prosseguir para US3/US4

### Incremental Delivery

1. Setup + Foundational → toda a base de instrumentação pronta
2. US1 → trace de ponta a ponta navegável (MVP funcional)
3. US2 → gargalos de performance identificáveis (completa o par P1)
4. US3 → falhas de comunicação diagnosticáveis
5. US4 → erros de aplicação correlacionados ao trace
6. Polish → amostragem de produção, resiliência validada, benchmark de overhead

---

## Notes

- [P] = arquivos diferentes, sem dependência de tarefas incompletas
- [Story] mapeia a tarefa à história de usuário correspondente para rastreabilidade
- Nenhum atributo de span deve violar a allowlist/denylist de `data-model.md` — válido para toda tarefa de implementação, não apenas as de US4
- Verificar que os testes falham antes de implementar (T029-T031, T045, T048-T049, T053-T054, T064, T067)
- Parar em qualquer checkpoint para validar a história isoladamente antes de prosseguir
