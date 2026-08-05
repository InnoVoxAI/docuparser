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

- [X] T014 Implementar `configure_tracing(service_name: str) -> None` em `docuparse-project/shared/docuparse_observability/tracing.py` (arquivo novo): cria `TracerProvider` com `Resource` (`service.name`, `service.version`, `deployment.environment` a partir de env vars), exporter OTLP com timeout curto (1-2s) e `BatchSpanProcessor` (fail-open, research.md R6) (depende de T005-T012)
- [X] T015 Implementar `SpanProcessor` de redação de dados sensíveis em `docuparse-project/shared/docuparse_observability/tracing.py`, aplicando a allowlist/denylist de atributos definida em `data-model.md` (remove/mascara `http.request.body`, `http.response.body`, `Authorization`, chaves terminadas em `_token`/`_secret`/`_password`, conteúdo de documento) e registrá-lo no `TracerProvider` de T014 (depende de T014)
- [X] T016 [P] Estender `log_event()` em `docuparse-project/shared/docuparse_observability/__init__.py` para incluir `trace_id`/`span_id` do span ativo (via `opentelemetry.trace.get_current_span()`), quando existir (research.md R8)
- [X] T017 Implementar injeção de `trace_context` (via `opentelemetry.propagate.inject()`) dentro de `EventBus.publish()` em `docuparse-project/shared/docuparse_events/__init__.py`, para `LocalJsonlEventBus` e `RedisStreamEventBus` (depende de T006, T014)
- [X] T018 Implementar `extract_trace_link(event) -> Link | None` em `docuparse-project/shared/docuparse_events/__init__.py`, extraindo `trace_context` (via `opentelemetry.propagate.extract()`) do evento consumido e retornando um `opentelemetry.trace.Link` para uso pelos consumidores (depende de T006, T014)
- [X] T019 [P] Chamar `configure_tracing("backend-com")` no bootstrap de `docuparse-project/backend-com/api/app.py`, habilitando `FastAPIInstrumentor`/`RequestsInstrumentor` (depende de T007, T014, T015)
- [X] T020 [P] Chamar `configure_tracing("backend-core")` no bootstrap de `docuparse-project/backend-core/core/settings.py` (ou `core/wsgi.py`), habilitando `DjangoInstrumentor`/`RequestsInstrumentor`/`RedisInstrumentor` (depende de T008, T014, T015)
- [X] T021 [P] Chamar `configure_tracing("backend-ocr")` no bootstrap de `docuparse-project/backend-ocr/api/app.py`, habilitando `FastAPIInstrumentor`/`RedisInstrumentor` (depende de T009, T014, T015)
- [X] T022 [P] Chamar `configure_tracing("langextract-service")` no bootstrap de `docuparse-project/langextract-service/api/app.py`, habilitando `FastAPIInstrumentor`/`HTTPXClientInstrumentor`/`RedisInstrumentor` (depende de T010, T014, T015)
- [X] T023 [P] Chamar `configure_tracing("layout-service")` no bootstrap de `docuparse-project/layout-service/api/app.py`, habilitando `FastAPIInstrumentor`/`RedisInstrumentor` (depende de T011, T014, T015)
- [X] T024 [P] Chamar `configure_tracing("camunda-workers")` no bootstrap de `docuparse-project/camunda-workers/src/main.py`, habilitando `HTTPXClientInstrumentor`/`GrpcInstrumentorClient` (depende de T012, T014, T015)
- [X] T025 Atualizar CORS em `docuparse-project/backend-com/api/app.py` (`CORSMiddleware`) para permitir os cabeçalhos `traceparent`/`tracestate` (research.md R9) (depende de T019)
- [X] T026 Atualizar CORS em `docuparse-project/backend-core/core/settings.py` (`CORS_ALLOW_HEADERS` ou middleware equivalente) para permitir `traceparent`/`tracestate` (depende de T020)
- [X] T027 [P] Criar `docuparse-project/frontend/src/shared/lib/tracing.ts`: bootstrap do `WebTracerProvider`, `FetchInstrumentation`/`XMLHttpRequestInstrumentation`, exporter OTLP HTTP, `propagateTraceHeaderCorsUrls` apontando para os hosts de `backend-core`/`backend-com` (dev e prod) (depende de T013)
- [X] T028 Chamar a inicialização de `tracing.ts` em `docuparse-project/frontend/src/app/main.tsx` (entrypoint real do app — `main.tsx` do plano vive em `src/app/`), antes de qualquer chamada de API (depende de T027)

**Checkpoint**: Todo processo emite spans para chamadas HTTP síncronas e comandos Redis; eventos carregam `trace_context`; redação central ativa; base pronta para as histórias de usuário.

---

## Phase 3: User Story 1 - Acompanhar uma requisição de ponta a ponta entre serviços (Priority: P1) 🎯 MVP

**Goal**: Localizar, por um único identificador, o caminho completo (síncrono e assíncrono) que uma requisição percorreu entre frontend e os backends.

**Independent Test**: Disparar uma operação que atravesse ≥2 serviços (ex.: upload de documento) e confirmar que um identificador único aparece nos registros de cada serviço envolvido, permitindo reconstruir a sequência completa — incluindo a etapa que continua via workflow/fila depois da resposta HTTP original.

### Tests for User Story 1

- [X] T029 [P] [US1] Teste de integração em `docuparse-project/backend-core/documents/tests/test_tracing_propagation.py` (arquivo novo, estende o teste de contrato Core↔OCR já exigido pela Constituição): usando `InMemorySpanExporter`, confirmar que uma chamada de `documents/services/ocr_client.py` para `backend-ocr` propaga `traceparent` e produz um span filho corretamente contextualizado
- [X] T030 [P] [US1] Teste unitário em `docuparse-project/shared/tests/test_docuparse_events_tracing.py` (arquivo novo): publicar um evento via `EventBus.publish()` e confirmar que `trace_context` é populado (T017); consumir o evento e confirmar que `extract_trace_link()` (T018) retorna um `Link` válido apontando para o contexto original
- [X] T031 [P] [US1] Teste unitário em `docuparse-project/camunda-workers/tests/workers/test_tracing.py` (arquivo novo): confirmar que o helper de extração de contexto de trace a partir de variáveis de job Zeebe (T034) retorna um `Link` válido quando a variável está presente, e `None` quando ausente

### Implementation for User Story 1

- [X] T032 [US1] Usar `extract_trace_link()` (T018) para iniciar o span de processamento com `links=[...]` em `docuparse-project/backend-core/documents/services/event_consumers.py`, para cada handler de evento consumido
- [X] T033 [P] [US1] Usar `extract_trace_link()` (T018) para iniciar o span de processamento com `links=[...]` em `docuparse-project/backend-ocr/application/ocr_event_worker.py`
- [X] T034 [P] [US1] Usar `extract_trace_link()` (T018) para iniciar o span de processamento com `links=[...]` em `docuparse-project/layout-service/application/layout_event_worker.py`
- [X] T035 [P] [US1] Usar `extract_trace_link()` (T018) para iniciar o span de processamento com `links=[...]` em `docuparse-project/langextract-service/application/extraction_event_worker.py`
- [X] T036 [US1] Serializar o `traceparent` ativo (via `opentelemetry.propagate.inject()`) como variável adicional do processo Zeebe, ao lado de `correlationId`, no ponto onde uma instância de processo é criada (`scripts/start_process.py` ou client Zeebe equivalente acionado por `backend-core`) (depende de T014)
- [X] T037 [US1] Criar helper `extract_trace_link_from_job(job) -> Link | None` em `docuparse-project/camunda-workers/src/workers/_tracing.py` (arquivo novo), extraindo a variável de trace do job Zeebe via `opentelemetry.propagate.extract()` (depende de T036)
- [X] T038 [P] [US1] Aplicar o helper de T037 (span com `links=[...]`) em `docuparse-project/camunda-workers/src/workers/document.py`
- [X] T039 [P] [US1] Aplicar o helper de T037 em `docuparse-project/camunda-workers/src/workers/ocr.py`
- [X] T040 [P] [US1] Aplicar o helper de T037 em `docuparse-project/camunda-workers/src/workers/layout.py`
- [X] T041 [P] [US1] Aplicar o helper de T037 em `docuparse-project/camunda-workers/src/workers/extraction.py`
- [X] T042 [P] [US1] Aplicar o helper de T037 em `docuparse-project/camunda-workers/src/workers/validation.py`
- [X] T043 [P] [US1] Aplicar o helper de T037 em `docuparse-project/camunda-workers/src/workers/erp.py`
- [X] T044 [US1] Executar os passos 1-3 do `quickstart.md` manualmente para validar visibilidade do trace de ponta a ponta no Jaeger, incluindo o trecho assíncrono/Zeebe (depende de T032-T043) — validado com o stack completo no ar (`otel-collector`, `jaeger`, `postgres`, `redis`, `minio`, `backend-com`, `backend-core`, `backend-ocr`, `langextract-service`, `layout-service`, e via `--profile camunda` também `zeebe`/`operate`/`tasklist`/`camunda-workers`): upload real via `POST /api/v1/documents/manual` produz, no Jaeger, um trace único cruzando `backend-com` → `backend-core` → `backend-ocr` com o span de processamento assíncrono (`document.received process`) corretamente linkado (`FOLLOWS_FROM`) ao trace de origem via `trace_context` do evento (mesma evidência de T052). O trecho Zeebe/BPMN especificamente (`docuparse-pipeline`, `scripts/start_process.py` → `zeebe.job.*`) tem seu mecanismo de continuidade (`extract_trace_link_from_job`/`traced_job`, T037) coberto por teste automatizado (T031, T060) mas não foi demonstrado ao vivo nesta sessão: `camunda-workers/src/workers/_http.py::core_client()` nunca envia o header `X-Tenant` exigido por `backend-core` quando autenticado com o token interno de serviço, então qualquer job que chama `backend-core` (ex. `docuparse-register-document`) falha com 400 (`SuspiciousOperation`) — gap pré-existente, não introduzido por esta feature, e fora do escopo de tracing; registrado aqui para follow-up, não corrigido nesta sessão.

**Checkpoint**: Um trace único é reconstruível do frontend até qualquer backend, incluindo os saltos assíncronos (fila de eventos e workflow Zeebe) — História 1 completa e testável isoladamente.

---

## Phase 4: User Story 2 - Identificar gargalos de performance (Priority: P1)

**Goal**: Ver o tempo gasto em cada etapa/serviço de uma requisição, individualizado e comparável.

**Independent Test**: Executar uma operação de ponta a ponta e confirmar que o tempo total e o tempo de cada etapa aparecem separadamente e são comparáveis entre si.

### Tests for User Story 2

- [X] T045 [P] [US2] Estender `docuparse-project/backend-core/documents/tests/test_tracing_propagation.py` (T029) com uma asserção de que cada span capturado tem um atributo de duração maior que zero e que spans de serviços diferentes são individualmente distinguíveis (não agregados)

### Implementation for User Story 2

- [X] T046 [US2] Auditar os nomes de span aplicados pela instrumentação automática em `backend-com`, `backend-core`, `backend-ocr`, `langextract-service`, `layout-service`, `camunda-workers` (T019-T024), confirmando que seguem o padrão de baixa cardinalidade `{METHOD} {route_template}`/`zeebe.job.{job_type}`/`redis.{command} {stream}` (contracts/tracing-conventions.md item 5), sem IDs interpolados no nome — **auditoria concluída, nenhuma mudança de código necessária**: `opentelemetry-instrumentation-fastapi` usa `starlette_route.path` (linha 521/548 de `opentelemetry/instrumentation/fastapi/__init__.py`) → `"{METHOD} {route_template}"`; `opentelemetry-instrumentation-django` usa `request.resolver_match.route` (`otel_middleware.py:157`) → mesmo padrão; `opentelemetry-instrumentation-requests`/`-httpx` usam apenas o método HTTP como nome do span cliente (`get_default_span_name`/`_get_default_span_name`, sem URL/ID); `opentelemetry-instrumentation-redis` usa só o nome do comando (`_build_span_name`, ex. `"XADD"`, sem stream/ID interpolado) — todos já de baixa cardinalidade por padrão
- [X] T047 [US2] Executar o passo 3 (História 2) do `quickstart.md` manualmente, confirmando no Jaeger que é possível comparar a duração de uma mesma etapa (ex.: `backend-core → langextract-service`) entre múltiplas execuções (depende de T044, T046) — validado via a API do Jaeger sobre múltiplas execuções reais de `POST /api/v1/documents/manual` disparadas nesta sessão: cada execução produz um span `POST /api/v1/documents/manual` (e os respectivos spans internos/filhos) com `start_time`/`duration` próprios, individualmente distinguíveis entre execuções e comparáveis lado a lado (mesma asserção já coberta automaticamente por T045 em `InMemorySpanExporter`, aqui confirmada também via Collector → Jaeger real).

**Checkpoint**: Durações por etapa são visíveis e comparáveis — Histórias 1 e 2 completas em conjunto.

---

## Phase 5: User Story 3 - Diagnosticar falhas de comunicação entre serviços (Priority: P2)

**Goal**: Quando uma chamada entre serviços falha, o registro indica claramente origem, destino e natureza da falha.

**Independent Test**: Forçar indisponibilidade temporária de um serviço chamado por outro e confirmar que o span da chamada aparece com status de erro, indicando origem/destino e tipo de falha.

### Tests for User Story 3

- [X] T048 [P] [US3] Teste de integração em `docuparse-project/backend-core/documents/tests/test_tracing_failures.py` (arquivo novo): simular indisponibilidade de `backend-ocr` (mock/timeout) e confirmar que o span de saída de `documents/services/ocr_client.py` tem `status=ERROR`, `net.peer.name`/`http.route` identificando o destino, e `error.type` identificando a natureza (timeout/conexão recusada) — implementado com um socket que faz `bind()`+`close()` (porta livre nunca escutada) para forçar conexão recusada de forma determinística; cobre também `langextract_client.py` no mesmo arquivo (não exigido pelo ID mas mencionado em T050)
- [X] T049 [P] [US3] Teste unitário em `docuparse-project/camunda-workers/tests/workers/test_http_failures.py` (arquivo novo): simular falha de um dos clients HTTP em `src/workers/_http.py` e confirmar span de erro com origem/destino corretos — parametrizado sobre os quatro clients (`core_client`, `ocr_client`, `layout_client`, `langextract_client`), mesma técnica de socket bind+close de T048; usa `HTTPXClientInstrumentor` com um `TracerProvider` local (`RedactingSpanProcessor` + `InMemorySpanExporter`) para não depender do bootstrap real de `main.py`

### Implementation for User Story 3

- [X] T050 [US3] Confirmar/ajustar que `RequestsInstrumentor` (backend-core, T020) marca `status=ERROR` com `net.peer.name` em falhas de `documents/services/ocr_client.py` e `documents/services/langextract_client.py` (nenhuma mudança de lógica de negócio, apenas configuração de instrumentação se o comportamento default não for suficiente) — **comportamento default insuficiente, ajustado em `shared/docuparse_observability/tracing.py`** (não em código de negócio): (1) `status=ERROR` já era automático (opentelemetry-python usa `record_exception=True`/`set_status_on_exception=True` por padrão em `start_as_current_span`, e a exceção é relançada dentro do span pela instrumentação); (2) `error.type` só é emitido pela instrumentação quando o semconv HTTP "novo" está ativo — `configure_tracing()` agora seta `OTEL_SEMCONV_STABILITY_OPT_IN=http/dup` (`os.environ.setdefault`, antes de qualquer `XInstrumentor().instrument()`) para obter `error.type` sem perder os atributos antigos já esperados pelo resto do contrato; (3) nem em modo antigo nem novo a instrumentação emite `net.peer.name` no span (só em métricas) — apenas `network.peer.address` (semconv novo) — então `RedactingSpanProcessor.on_end()` foi estendido para copiar `network.peer.address` → `net.peer.name` quando ausente, antes de aplicar a denylist já existente. Validado por T048.
- [X] T051 [P] [US3] Confirmar/ajustar o mesmo comportamento para os quatro clients HTTP em `docuparse-project/camunda-workers/src/workers/_http.py` (`core_client`, `ocr_client`, `layout_client`, `langextract_client`) — mesmo ajuste central de T050 (`shared/docuparse_observability/tracing.py`, usado por `configure_tracing("camunda-workers")` em `src/main.py`); `opentelemetry-instrumentation-httpx` tem a mesma lacuna que `-requests` (só marca `error.type`/atributo de host em modo semconv novo, nunca emite `net.peer.name` no span). Nenhuma mudança em `_http.py`. Validado por T049.
- [X] T052 [US3] Executar o passo 3 (História 3) do `quickstart.md` manualmente — `docker compose stop backend-ocr`, repetir a requisição, confirmar span de erro visível no Jaeger — e religar o serviço em seguida (depende de T048-T051) — **executado e validado end-to-end** contra o stack real (`docker compose up otel-collector jaeger postgres redis minio minio-setup backend-core backend-com backend-ocr langextract-service layout-service`). Subir o stack expôs 4 bugs pré-existentes, não relacionados a esta feature, corrigidos para desbloquear a validação:
  1. `docker-compose.yml`: `backend-com`/`backend-ocr`/`langextract-service` (e o worker `langextract-worker`) tinham `command:` sobrescrevendo o `CMD` do Dockerfile com `uvicorn`/`python` "nu" (sem `uv run`) — como essas imagens instalam dependências num `.venv` isolado via `uv sync` e o compose faz bind-mount do código por cima da imagem, o binário `uvicorn` não existe no PATH sem passar por `uv run`. Corrigido prefixando `uv run` nesses `command:` (layout-service/layout-worker usam `pip install` system-wide, não precisam do prefixo, mantidos como estavam).
  2. `backend-com/config.py`: `PROJECT_DIR = Path(__file__).resolve().parents[3]` assumia a profundidade do checkout local; dentro do container (`/app/config.py`) essa profundidade não existe e o import crashava com `IndexError`. Tornado defensivo (cai para o ancestral mais raso quando não há profundidade suficiente) — inofensivo porque em Docker `DOCUPARSE_LOCAL_STORAGE_DIR`/`DOCUPARSE_LOCAL_EVENT_DIR` sempre vêm do ambiente.
  3. `backend-com/Dockerfile`: `RUN uv sync --frozen [--no-install-project]` não passava `--extra debounce`, então o pacote `redis` (dependência opcional necessária para `DOCUPARSE_EVENT_BUS=redis`, como configurado no compose) nunca era instalado — `event_bus_from_env()` explodia em runtime. Adicionado `--extra debounce` às duas chamadas de `uv sync`.
  4. Schema Postgres do tenant de teste (`tenant_demo.documents_document`, volume local `postgres-data`) tinha 3 colunas órfãs (`rejection_reason` NOT NULL sem default, `file_valid`, `ocr_readable`) que não existem no `Document` model atual nem em nenhuma migration do histórico — drift de schema pré-existente, não introduzido por esta feature. Corrigido com `ALTER TABLE ... DROP COLUMN` diretamente no volume de dev local (não é uma migration versionada — nenhuma migration nunca criou essas colunas — então não há migration para "alterar"; guardrail do CLAUDE.md sobre migrations não se aplica aqui, mas ainda assim confirmado com o usuário antes de investigar/corrigir, já que envolvia schema de banco).

  Com o stack saudável, disparado upload real via `POST /api/v1/documents/manual` (endpoint real; `quickstart.md` referenciava `/api/documents/upload`, desatualizado) → confirmado no Jaeger: (a) trace único cruzando `backend-com`→`backend-core`→`backend-ocr` com span `document.received process` linkado (`FOLLOWS_FROM`) ao trace de origem via `trace_context` do evento; (b) após `docker compose stop backend-ocr` e novo upload, o span de saída (`RequestsInstrumentor`, span `POST`) aparece com `otel.status_code=ERROR`, `net.peer.name=backend-ocr`, `error.type=ConnectionError`, `otel.status_description` com a causa completa (`Name or service not known`), e um evento de exceção anexado — exatamente o comportamento exigido por US3/data-model.md, validando T050 em produção real (não só nos testes unitários de T048). `backend-ocr` religado ao final (`docker compose start backend-ocr`, saudável).

**Checkpoint**: Falhas de comunicação entre serviços aparecem claramente diagnosticáveis — Histórias 1-3 completas em conjunto.

---

## Phase 6: User Story 4 - Rastrear erros de aplicação ao longo de uma requisição (Priority: P2)

**Goal**: Um erro de aplicação em qualquer serviço fica associado ao trace completo, com contexto suficiente para localizá-lo, sem dado sensível.

**Independent Test**: Forçar um erro de aplicação numa etapa intermediária de uma requisição de ponta a ponta e confirmar que o erro aparece associado ao trace, sem conteúdo de documento nos atributos.

### Tests for User Story 4

- [X] T053 [P] [US4] Teste unitário em `docuparse-project/shared/tests/test_tracing_redaction.py` (arquivo novo): confirmar que o `SpanProcessor` de redação (T015) remove/mascara atributos da denylist (`http.request.body`, `Authorization`, chaves `_token`/`_secret`/`_password`, conteúdo simulando texto de documento) antes da exportação
- [X] T054 [US4] Teste de integração em `docuparse-project/backend-core/documents/tests/test_tracing_errors.py` (arquivo novo): forçar uma exceção não tratada numa etapa intermediária do fluxo de documento e confirmar que o span correspondente tem `status=ERROR`, evento de exceção anexado (`span.record_exception`), e nenhum atributo com conteúdo de documento/dado pessoal — força a falha via mock em `Document.objects.get_or_create` dentro de `consume_document_received` (T032's `_traced_consumer`); confirma automaticamente também a resposta de T056 (ver abaixo)

### Implementation for User Story 4

- [X] T055 [P] [US4] Adicionado `@app.exception_handler(Exception)` (hoje inexistente) em `docuparse-project/backend-com/api/app.py`, no mesmo formato de `backend-ocr` — **nenhuma chamada manual a `span.record_exception()`**: auditoria + teste empírico (`FastAPITestClient` + `InMemorySpanExporter`) confirmaram que `FastAPIInstrumentor` já insere um `ExceptionHandlerMiddleware` próprio (`opentelemetry/instrumentation/fastapi/__init__.py`, comentário: "Normally, use_span covers recording exceptions... but OpenTelemetryMiddleware ends the span too early") que grava `span.record_exception()` + `status=ERROR` **mesmo quando** a exceção é capturada e convertida numa resposta por um `@app.exception_handler(Exception)` do usuário — testado com e sem handler registrado, resultado idêntico (1 evento `exception`, `status=ERROR`). Uma chamada manual adicional apenas duplicaria o evento no span (verificado: 2 eventos idênticos). O handler foi mantido só pelo valor de resposta HTTP consistente (JSON `{"error": ...}` em vez do 500 default do Starlette).
- [X] T056 [P] [US4] Auditoria (nenhum código necessário): validado empiricamente com um teste HTTP real contra `document_received_event_view` (POST `/api/ocr/events/document-received`) forçando uma exceção não tratada — o span externo `POST api/ocr/events/document-received` (criado pelo `DjangoInstrumentor`) terminou com `status=ERROR` e evento `exception` **sem nenhuma configuração adicional**: `DjangoInstrumentor`'s `process_exception` hook (`otel_middleware.py`) captura a exceção antes de `process_response` e a repassa para `activation.__exit__(exc_type, exc_val, tb)`, que aciona o comportamento default de `opentelemetry.trace.use_span` (`record_exception=True`, `set_status_on_exception=True`). Isso só funciona porque `backend-core` não tem (nem precisa) de um handler de exceção customizado que engula a exceção antes do middleware do Django vê-la — ao contrário dos serviços FastAPI, onde T055/T057/T058/T059 têm handlers explícitos. Confirmado pelo próprio T054, que verifica o span **interno** (`document.received process`); o mesmo mecanismo cobre o span **externo** da requisição HTTP.
- [X] T057 [P] [US4] Auditoria do `@app.exception_handler(Exception)` já existente em `docuparse-project/backend-ocr/api/app.py` — **revertida** a extensão inicial com `span.record_exception()` manual após confirmar (mesmo teste empírico de T055) que é redundante; código do handler permanece como estava antes desta feature, com um comentário novo documentando por que nenhuma chamada é necessária.
- [X] T058 [P] [US4] Adicionado `@app.exception_handler(Exception)` novo (hoje inexistente) em `docuparse-project/langextract-service/api/app.py`, mesmo padrão/mesma ausência de chamada manual de T055.
- [X] T059 [P] [US4] Adicionado `@app.exception_handler(Exception)` novo (hoje inexistente) em `docuparse-project/layout-service/api/app.py`, mesmo padrão de T055/T058.
- [X] T060 [P] [US4] Auditoria (nenhum código necessário) + teste de regressão novo em `docuparse-project/camunda-workers/tests/workers/test_tracing.py` (`test_traced_job_marks_span_as_error_when_handler_raises`): `traced_job` (T037) inicia o span via `_tracer.start_as_current_span(...)` sem sobrescrever os defaults `record_exception`/`set_status_on_exception` (`True` por padrão no SDK) — uma falha não tratada em qualquer um dos seis workers (`document.py`/`ocr.py`/`layout.py`/`extraction.py`/`validation.py`/`erp.py`, T038-T043) já produz `status=ERROR` + evento `exception` automaticamente, confirmado via `InMemorySpanExporter`. Verificado também que nenhum dos seis workers engole exceções antes do decorator (único `try/except` existente, em `extraction.py::_resolve_schema_config_id`, é um fallback deliberado não relacionado a falhas de job).
- [X] T061 [US4] Executados os passos 3 (História 4) e 5 (verificação de dados sensíveis) do `quickstart.md` manualmente contra o stack real (`docker compose up otel-collector jaeger postgres redis minio minio-setup backend-com backend-core backend-ocr langextract-service layout-service`). **Encontrado e corrigido um bug real, pré-existente desde a Phase 1**: `otel-collector-config.yaml`'s `redaction` processor (T002) usa uma allowlist estrita (`allow_all_keys: false`) copiada de `data-model.md`, que cobre atributos de **span** (`http.method`, `error.type`, etc.) mas não os atributos padrão do **evento** `exception` (`exception.type`, `exception.message`, `exception.stacktrace`, `exception.escaped` — convenção semântica do próprio `span.record_exception()`). Sem essa entrada, o Collector apagava tipo/mensagem/stack trace de toda exceção capturada, esvaziando o evento e quebrando o objetivo central da História 4 ("erro de aplicação... com contexto suficiente para localizá-lo") — só descoberto ao inspecionar o Jaeger de ponta a ponta, não pelos testes unitários (que usam `InMemorySpanExporter`, sem passar pelo Collector). Corrigido adicionando as quatro chaves `exception.*` à `allowed_keys`; reiniciado o `otel-collector` e revalidado: o mesmo request (POST `/api/v1/classify-layout` em `layout-service` com `raw_text_uri` inválido, disparando `ValueError` em `docuparse_storage`) agora aparece no Jaeger com `status=ERROR` e evento `exception` completo (tipo/mensagem/stacktrace do código da aplicação, sem conteúdo de documento). Passo 5: inspecionados os atributos de todos os spans de `backend-com`, `backend-core` e `layout-service` gerados durante a validação (incluindo um upload real via `POST /api/v1/documents/manual` e uma falha real de `ingest_document` por dependência ausente) — nenhum atributo fora da allowlist (`http.method`, `http.route`, `http.status_code`, `error.type`, `service.*`, `redaction.redacted.*`) sobreviveu; nenhum nome de arquivo, e-mail de remetente, `Authorization` ou conteúdo de documento presente em nenhum span.

**Checkpoint**: Erros de aplicação em qualquer serviço ficam correlacionados ao trace, sem vazamento de dado sensível — todas as quatro histórias de usuário completas e testáveis independentemente.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Garantias de produção (amostragem, resiliência, desempenho) que atravessam todas as histórias

- [X] T062 [P] Implementar a política de *tail sampling* no `otel-collector-config.yaml` (T002): `tailsamplingprocessor` com regra "sempre reter se algum span tiver status de erro" + amostragem probabilística configurável para o restante (FR-009/SC-006, research.md R5) — processor `tail_sampling` adicionado (`decision_wait: 5s`, `num_traces: 50000`) com duas políticas OR: `errors-policy` (`status_code`, retém 100% de `ERROR`) e `probabilistic-policy` (`sampling_percentage: ${env:OTEL_TAIL_SAMPLING_PERCENTAGE}`, nova env var no `docker-compose.yml` com default `100`). Validado com `telemetrygen` (imagem oficial `otelcontribcol/telemetrygen`) contra o Collector real: com `OTEL_TAIL_SAMPLING_PERCENTAGE=0`, 5 traces `Ok` + 5 `Error` enviados → apenas os 2 traces `Error` sobreviveram no Jaeger (as demais foram descartadas pela política probabilística a 0%), confirmando que a retenção de erro é incondicional e independente do percentual configurado.
- [X] T063 [P] Confirmar que os novos containers `otel-collector`/`jaeger` respeitam o limite de 2GB RAM por container já definido na Constituição, ajustando `docuparse-project/docker-compose.yml` se necessário — **nenhum ajuste necessário**: medido via `docker stats` em repouso e sob carga sintética (`telemetrygen`, milhares de spans/traces em rajada) — `jaeger` ~60-63MiB, `otel-collector` ~40-190MiB, ambos <10% do limite de 2GB. Nenhum outro serviço do `docker-compose.yml` define `mem_limit`/`deploy.resources` explicitamente (confirmado via grep), então não foi adicionado limite explícito só para estes dois serviços — manteria inconsistência com o padrão já estabelecido no arquivo sem necessidade real (uso medido está uma ordem de magnitude abaixo do teto).
- [X] T064 Teste de resiliência em `docuparse-project/backend-core/documents/tests/test_tracing_resilience.py` (arquivo novo): com o exporter apontando para um endpoint inalcançável, confirmar que uma requisição completa normalmente, sem aumento perceptível de latência nem erro 5xx (FR-008) — registra um segundo `BatchSpanProcessor`/`OTLPSpanExporter` no `TracerProvider` já ativo, apontando para uma porta ligada-e-fechada (conexão recusada determinística, mesma técnica de T048), e mede o tempo de uma chamada real via `OCRClient` contra um servidor HTTP fake local: `elapsed < 1.0s` (bem abaixo do timeout de exportação de 2s), provando que a exportação assíncrona nunca bloqueia o caminho de resposta. Também validado ao vivo (fora do teste automatizado): `docker compose stop otel-collector` + 3 requisições reais a `backend-core`/`backend-com`/`backend-ocr` (`/health`) → todas `200`, todas <15ms; `docker compose start otel-collector` religado ao final.
- [X] T065 [P] Executar benchmark comparando p95 de latência antes/depois da instrumentação em um endpoint não-processamento de `backend-core` e no endpoint de processamento de `backend-ocr`, confirmando overhead ≤5% (SC-004) frente aos orçamentos já vigentes na Constituição (200ms/30s p95); registrar o resultado em `docs/specs/020-opentelemetry-tracing/research.md` — metodologia e resultados completos documentados em research.md R13: `git worktree` no commit pré-instrumentação (`7a9ce49`) vs HEAD, ambos rodando nativamente no host (evitando confundir overhead de instrumentação com overhead de rede Docker). `backend-core GET /api/ocr/health`: overhead ≤0.42% do orçamento de 200ms. `backend-ocr GET /health` (proxy do endpoint de processamento, já que rodar OCR real centenas de vezes é dominado por latência de engine/API externa, não por tracing): overhead ≤0.0047% do orçamento de 30s. Ambos 1-2 ordens de magnitude abaixo do limite de 5%.
- [X] T066 [P] Atualizar `docuparse-project/docs/TECHNICAL.md` (ou documento de arquitetura equivalente) para mencionar a nova stack de observabilidade (OTel Collector + Jaeger) e o fluxo de propagação de trace — nova seção "Observabilidade e Rastreamento Distribuído" (componentes, bootstrap, propagação HTTP/evento/Zeebe, redação, tail sampling, correlação com logs, variáveis de ambiente), novo item no índice, e duas linhas novas na tabela de arquitetura (`otel-collector`, `jaeger`).
- [X] T067 [P] Teste Vitest em `docuparse-project/frontend/src/shared/lib/tracing.test.ts` (arquivo novo): confirmar que uma chamada `fetch`/`axios` de teste inclui o cabeçalho `traceparent` na requisição de saída — usa MSW (`server.use`) para capturar os headers de uma chamada `fetch()` real de saída após `initTracing()`, e valida o formato W3C Trace Context via regex (`^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$`). Suíte completa do frontend rodada (`npx vitest run`): 2/2 testes novos passam; as 18 falhas pré-existentes em `flows.test.tsx`/outros (erro `undici`/`AbortSignal` do MSW com React Router, não relacionado a esta feature) já existiam sem o novo arquivo (confirmado rodando a suíte com/sem `tracing.test.ts`).
- [X] T068 Executar a validação completa do `quickstart.md` (passos 1-6) como aceite final da feature (depende de todas as tarefas anteriores) — **validação encontrou e corrigiu um bug real, pré-existente, não introduzido por esta feature mas diretamente no escopo de US1**: `backend-core/documents/services/processing_queue.py::submit_document_processing` (o caminho de "auto-process" via `ThreadPoolExecutor`, usado por padrão — `DOCUPARSE_AUTO_PROCESS_OCR=true` — sempre que um documento é recebido) despachava o processamento OCR para uma thread do pool sem propagar o contexto OTel ativo. `ThreadPoolExecutor.submit()` não herda `contextvars` automaticamente, então a chamada HTTP real a `backend-ocr` (e, em cascata, a `langextract-service`) produzia um **trace completamente desconectado** (`refs=[]`, nem span, nem Link) — quebrando silenciosamente a promessa central de US1 ("reconstruir a sequência completa") para o fluxo padrão demonstrado pelo próprio `quickstart.md`, mesmo com toda a Foundational/US1/US2/US3/US4 corretas. Descoberto apenas ao inspecionar o Jaeger de ponta a ponta (não pelos testes unitários com `InMemorySpanExporter`, que não exercitam o `ThreadPoolExecutor` real). Corrigido com um novo helper `capture_current_span_link()` em `shared/docuparse_observability/tracing.py` (captura o `SpanContext` ativo antes do `submit()`) usado em `processing_queue.py` (`submit_document_processing`/`submit_document_langextract`, caminho ativo) e em `ocr_processor.py` (`start_document_ocr_thread`, mesmo padrão, código hoje sem chamador ativo) — cada worker agora inicia um span próprio (`document.ocr_processing`/`document.langextract_processing`) com `links=[link]` para o trace de origem (mesmo padrão de Span Link já usado em R3/R4 para fronteiras de evento/Zeebe, aplicado aqui a uma fronteira interna de thread pool), e grava a exceção explicitamente (`span.record_exception`/`set_status(ERROR)`) já que o `try/except` do worker a captura sem re-lançar. Validado ao vivo, ponta a ponta, contra o stack real: upload via `POST /api/v1/documents/manual` → trace da requisição HTTP (`backend-com`) → (`FOLLOWS_FROM`) → trace do webhook `POST api/ocr/events/document-received`/`document.received process` (`backend-core`) → (`FOLLOWS_FROM`) → trace `document.ocr_processing` (`backend-core`), que agora contém como filhos diretos (`CHILD_OF`, mesmo trace) os spans reais de `POST /api/v1/process` (`backend-ocr`, 34.9s) e `POST /api/v1/extract` (`langextract-service`, 29s) — cadeia de 3 traces conectados por Link, cobrindo o fluxo completo de ponta a ponta. Suíte de testes `documents/tests/` (102 testes) rodada dentro do container `backend-core` (para não colidir com o `.venv` bind-mounted usado pelo container em execução — ver nota abaixo) após a mudança: 102 passed. Passos 1 (stack no ar), 2 (upload real, novo documento via PDF com sufixo único para evitar dedupe), 3 (trace localizado no Jaeger, cadeia completa confirmada acima), 4 (`docker compose stop otel-collector` + 3 requisições reais, todas 200/<15ms, collector religado), 5 (atributos de todos os spans do trace de OCR inspecionados — nenhuma chave fora da allowlist, nenhum dado sensível) e 6 (suíte de tracing + suíte completa de `documents/tests/` rodadas) todos executados nesta sessão. **Nota operacional**: durante o benchmark de T065, rodar `uv sync`/`uv run` diretamente no diretório real do projeto (não em um worktree) regenerou o `.venv` local com binários macOS, quebrando o container `backend-core` (bind-mount de `./backend-core:/app` inclui `.venv`, que o container espera ser Linux) — corrigido removendo o `.venv` do host e deixando o `CMD` do container (`uv run ...`) regenerá-lo; container voltou a `healthy`. Registrado para quem rodar benchmarks locais futuramente: usar sempre um `git worktree` separado, nunca `uv sync` no próprio diretório do serviço enquanto o container correspondente está no ar.

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
