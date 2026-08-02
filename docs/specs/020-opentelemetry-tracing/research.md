# Research: Rastreamento Distribuído (OpenTelemetry) entre Serviços

## R1: Escopo técnico real inclui `layout-service` e `camunda-workers` como processos próprios, não como "código compartilhado"

O spec (`Assumptions`) agrupa `layout-service` junto de `contracts`/`shared` como "código compartilhado usado por eles". Na prática, `docuparse-project/layout-service` é um quinto serviço HTTP FastAPI independente (`api/app.py`, porta 8090) com seu próprio worker de eventos (`application/layout_event_worker.py`, serviço compose `layout-worker`), e `docuparse-project/camunda-workers` é o processo que efetivamente orquestra a jornada completa via Zeebe/BPMN (`bpmn/flow.bpmn`), fazendo chamadas HTTP para os quatro backends citados no spec (`src/workers/_http.py`: `core_client`, `ocr_client`, `layout_client`, `langextract_client`).

- **Decision**: Tratar `layout-service` como um sexto ponto de instrumentação HTTP (mesmo padrão dos outros serviços FastAPI) e `camunda-workers` como o ponto de instrumentação do salto assíncrono/orquestração (mesmo padrão dos consumidores de evento, mas via gRPC/Zeebe em vez de Redis Streams). Sem isso, as Histórias 3 e 4 do spec (falha de comunicação entre serviços, erro ao longo de uma requisição) ficariam com um buraco exatamente no ponto onde o BPMN encadeia a maior parte da jornada de um documento.
- **Rationale**: FR-007 e o Edge Case de processamento assíncrono exigem continuidade do trace através de "etapas de workflow/orquestração" — isso só é cumprível instrumentando o processo que executa essas etapas.
- **Alternatives considered**: Deixar `layout-service`/`camunda-workers` de fora nesta primeira entrega (menor escopo) — rejeitado porque quebraria justamente o trecho do fluxo mais difícil de depurar hoje (nenhum dos dois tem qualquer log estruturado consistente, ver R8).

## R2: SDKs e auto-instrumentação por tipo de serviço

Inventário (ver relatório de exploração): `backend-com`, `backend-ocr`, `langextract-service`, `layout-service` são FastAPI/Python 3.13 (uv); `backend-core` é Django 6/Python 3.13 (uv); `camunda-workers` é Python 3.12 (`requirements.txt`, `pyzeebe`, já usa `structlog`); `frontend` é React 19 + Vite + axios (TypeScript).

- **Decision**:
  - Serviços FastAPI (`backend-com`, `backend-ocr`, `langextract-service`, `layout-service`): `opentelemetry-instrumentation-fastapi` (spans de entrada) + `opentelemetry-instrumentation-httpx` ou `-requests` conforme o cliente HTTP já usado em cada um (`requests` em `backend-com`/`backend-core`, `httpx` em `camunda-workers`/`langextract-service` — confirmar por serviço na fase de implementação) + `opentelemetry-instrumentation-redis` (nos que publicam/consomem eventos).
  - `backend-core` (Django): `opentelemetry-instrumentation-django` + `opentelemetry-instrumentation-requests` (para `documents/services/ocr_client.py` e `langextract_client.py`) + `opentelemetry-instrumentation-redis` (para `event_consumers.py`).
  - `camunda-workers`: `opentelemetry-instrumentation-httpx` (para os clients em `_http.py`) + `opentelemetry-instrumentation-grpc` (canal do Zeebe) — não para medir o tempo de espera do Zeebe (isso é duração de negócio, não de infraestrutura), mas para que as chamadas HTTP de cada worker apareçam como spans filhos corretamente contextualizados (ver R3).
  - `frontend`: `@opentelemetry/sdk-trace-web` + `@opentelemetry/instrumentation-fetch` + `@opentelemetry/instrumentation-xml-http-request` (axios usa XHR por padrão no browser) + `@opentelemetry/exporter-trace-otlp-http`.
  - Em todos os serviços Python, o *bootstrap* (inicialização do `TracerProvider`, `Resource`, exporter, processors) é centralizado em uma função nova `configure_tracing(service_name: str)` dentro de `shared/docuparse_observability/tracing.py` (novo módulo), chamada uma vez no entrypoint de cada serviço — evita duplicar a mesma lógica de setup 6 vezes.
- **Rationale**: Usar as bibliotecas de auto-instrumentação oficiais do projeto OpenTelemetry evita reescrever propagação de contexto HTTP manualmente; centralizar o bootstrap em `shared/` segue o mesmo padrão já usado por `docuparse_events`/`docuparse_storage` (pacote compartilhado via `PYTHONPATH: /app:/contracts:/shared`).
- **Alternatives considered**: `opentelemetry-instrument` (auto-instrumentação via wrapper de CLI, zero código) — rejeitado como mecanismo principal porque não permite plugar o processor de redação de dados sensíveis (R7) nem o comportamento fail-open (R6) de forma explícita e testável; pode ser usado como atalho em dev, mas produção usa bootstrap explícito.

## R3: Propagação de contexto através do Zeebe/BPMN (camunda-workers) via *Span Links*, não *parent-child* direto

Uma instância de processo BPMN pode ficar pendente por minutos/horas entre a etapa que a inicia (ex.: `backend-core` recebendo `document.received` e chamando `scripts/start_process.py`, que já grava uma variável `correlationId`) e a etapa em que um worker Zeebe (`camunda-workers/src/workers/*.py`) de fato executa um job. Um span "pai" convencional ficaria aberto por toda essa espera, distorcendo duração e violando a semântica de span (unidade de trabalho ativo).

- **Decision**: No início do processo BPMN, serializar o `traceparent` ativo (via `opentelemetry.propagate.inject()`) como mais uma variável do processo Zeebe, ao lado de `correlationId`. Cada `job handler` em `camunda-workers/src/workers/*.py`, ao processar um job, extrai essa variável (`opentelemetry.propagate.extract(carrier=...)`) e inicia seu próprio span raiz com um **Link** (`opentelemetry.trace.Link`) para o contexto original, em vez de um span filho direto. O mesmo padrão vale para o consumo de eventos assíncronos via Redis Streams (R4).
- **Rationale**: É a prática recomendada do próprio OpenTelemetry para sistemas de fila/orquestração assíncrona (mensageria, cron, workflow) — preserva a possibilidade de navegar "de onde veio" um trace sem inflar artificialmente a duração aparente do span de origem.
- **Alternatives considered**: Span pai único cobrindo toda a jornada (rejeitado — duração enganosa, e ferramentas de trace tipicamente truncam/alertam em spans muito longos); ignorar propagação nesse trecho e aceitar traces desconectados (rejeitado — é exatamente o ponto de maior dificuldade de diagnóstico hoje, ver R1).

## R4: Propagação através do barramento de eventos (Redis Streams / `shared/docuparse_events`)

`shared/docuparse_events` já implementa `EventBus` (`LocalJsonlEventBus` para dev/teste, `RedisStreamEventBus` para produção) e todo evento herda de um schema base em `contracts/events/schemas.py` que já carrega `correlation_id: UUID`. A instrumentação automática de cliente Redis (`opentelemetry-instrumentation-redis`) traça os comandos `XADD`/`XREAD` em si, mas não entende a relação lógica "eu processei a mensagem X que veio de um publisher com contexto de trace Y".

- **Decision**: Adicionar um campo opcional `trace_context: dict[str, str] | None = None` ao schema base de evento em `contracts/events/schemas.py`. No momento da publicação (dentro de `docuparse_events`, no ponto em que o payload é serializado antes do `XADD`/append), popular esse campo via `opentelemetry.propagate.inject()`. No consumo (cada `*_event_worker.py`: `ocr_event_worker.py`, `layout_event_worker.py`, `extraction_event_worker.py`, `event_consumers.py` em backend-core), extrair o campo e iniciar o span de processamento com um Link para o contexto de origem (mesmo padrão de R3).
- **Rationale**: Reaproveita a infraestrutura de evento já existente (o campo entra ao lado de `correlation_id`, sem novo mecanismo de transporte) e mantém consistência com a decisão de Span Links do R3 para qualquer fronteira assíncrona.
- **Alternatives considered**: Unificar `correlation_id` (identificador de negócio já existente, também usado como variável de processo do Zeebe) com o `trace_id` do OTel — rejeitado por ora: são dois conceitos com ciclos de vida diferentes (um documento pode gerar múltiplos traces técnicos ao longo do tempo; `correlation_id` é estável para o documento inteiro). Ambos continuam coexistindo; o novo campo `trace_context` é adicional, não substitui `correlation_id`.

## R5: Amostragem — "100% dos erros preservados" exige *tail sampling* no Collector, não apenas *head sampling* no SDK

FR-009/SC-006 pedem redução de volume em produção sem nunca perder um trace que contenha erro. Amostragem *head-based* (decidida no SDK, no início do trace) não pode garantir isso porque a decisão é tomada antes de se saber se haverá erro.

- **Decision**: Implantar um **OpenTelemetry Collector** (`otel/opentelemetry-collector-contrib`) como novo serviço no `docker-compose.yml`, todos os serviços exportam via OTLP para o Collector (nunca direto para o backend de armazenamento), e o Collector aplica `tailsamplingprocessor` com uma política "sempre reter se algum span tiver status de erro", e uma segunda política de amostragem probabilística (ex.: 100% em dev, configurável em produção) para o restante.
- **Rationale**: É o mecanismo padrão e documentado do ecossistema OTel para esse requisito exato; concentra a lógica de amostragem num único ponto (o Collector), evitando reimplementar regras de retenção em cada um dos 6+ serviços.
- **Alternatives considered**: Amostragem 100% fixa em todos os ambientes (mais simples, mas não atende FR-009 "reduzir volume em ambientes de alto tráfego"); amostragem head-based simples (`TraceIdRatioBased`) sem Collector — mais barata de operar, porém não cumpre a garantia de 100% dos erros (rejeitada por violar SC-006 diretamente).

## R6: Comportamento *fail-open* quando a infraestrutura de coleta está indisponível (FR-008)

- **Decision**: Cada serviço usa `BatchSpanProcessor` (assíncrono, em thread/task separada) com o exportador OTLP configurado com timeout curto (1-2s) e sem retries bloqueantes; se o Collector estiver fora do ar, spans são descartados após o buffer encher, sem propagar exceção para o código de aplicação (comportamento padrão do SDK OTel quando configurado dessa forma, mas deve ser validado explicitamente em teste — ver `quickstart.md`/tasks futuras).
- **Rationale**: Cumpre FR-008 sem exigir código de aplicação consciente de tracing (a falha de exportação nunca deve aparecer como falha de requisição).
- **Alternatives considered**: `SimpleSpanProcessor` (síncrono, exporta no mesmo request) — rejeitado, acopla a latência do usuário à disponibilidade do Collector, o oposto do que FR-008 exige.

## R7: Redação de dados sensíveis (FR-006) via processor central em `shared/docuparse_observability`

Nenhum serviço hoje inclui conteúdo de documento diretamente em atributos de log/trace (os logs atuais só carregam `tenant_id`, `document_id`, `correlation_id`, `event_type` — ver `shared/docuparse_observability/__init__.py::log_event`), mas a instrumentação automática (ex.: `opentelemetry-instrumentation-requests`/`-httpx`) pode capturar cabeçalhos e corpos de requisição por padrão em algumas configurações.

- **Decision**: A função `configure_tracing()` (R2) registra um `SpanProcessor` central que roda antes da exportação e remove/mascara uma lista de chaves de atributo proibidas (ex.: `http.request.body`, `Authorization`, `document.content`, quaisquer chaves terminadas em `_token`/`_secret`), além de desabilitar explicitamente a captura de corpo de requisição/resposta nas bibliotecas de instrumentação HTTP (capturar apenas metadados: método, rota, status, duração).
- **Rationale**: Um único ponto de allowlist/denylist compartilhado (em vez de 6 configurações independentes) reduz o risco de um serviço vazar dado sensível por esquecimento.
- **Alternatives considered**: Confiar apenas na configuração default das bibliotecas de instrumentação (que já não capturam corpo por padrão) — insuficiente como garantia, já que não impede alguém de adicionar manualmente `span.set_attribute("document.text", ...)` no futuro; o processor central atua como rede de segurança adicional.

## R8: Correlação entre logs e traces

Hoje só `camunda-workers` usa logging estruturado de fato (`structlog`, chamadas como `log.info("camunda_workers_starting", ...)`). `backend-com` declara `structlog` como dependência mas nunca a usa (log “morto”). Os demais serviços usam `logging` puro sem formatação estruturada. O único helper compartilhado (`shared/docuparse_observability.log_event`) já serializa um JSON manual, mas não é chamado automaticamente por nenhum middleware.

- **Decision**: Estender `log_event()` (em `shared/docuparse_observability`) para incluir automaticamente `trace_id`/`span_id` do span ativo (via `opentelemetry.trace.get_current_span()`), quando existir um. Não faz parte desta feature migrar todos os serviços para logging estruturado completo (fora de escopo do spec) — apenas garantir que, onde `log_event()` já é ou passar a ser chamado, o trace/span fiquem anexados.
- **Rationale**: Entrega o valor de correlação log↔trace pedido implicitamente pelas Histórias 3/4 (diagnosticar falha/erro) sem expandir o escopo para uma reforma geral de logging, que é um projeto à parte.
- **Alternatives considered**: Migrar todos os serviços para `structlog` nesta feature — rejeitado por escopo (não é requisito do spec e infla significativamente o tamanho da entrega).

## R9: CORS precisa liberar o cabeçalho `traceparent` para propagação do frontend

O frontend, em produção, fala com `backend-core` e `backend-com` em origens diferentes (`docuparser-core.innovox.ai`, `docuparser-com.innovox.ai`), então o SDK Web precisa enviar o cabeçalho `traceparent` (W3C Trace Context) em requisições cross-origin, o que exige que o CORS de ambos os serviços liste `traceparent`/`tracestate` entre os cabeçalhos permitidos.

- **Decision**: Atualizar a configuração de CORS de `backend-com` (`CORSMiddleware`) e `backend-core` (`django-cors-headers`, se em uso, ou middleware equivalente já configurado) para incluir `traceparent`/`tracestate` em `allow_headers`/`CORS_ALLOW_HEADERS`. Configurar `propagateTraceHeaderCorsUrls` no SDK Web do frontend apontando para os hosts de `backend-core`/`backend-com` (dev e prod).
- **Rationale**: Sem isso, o navegador bloqueia o cabeçalho por CORS e a História 1 (rastreio ponta-a-ponta desde o frontend) fica quebrada silenciosamente só em produção (funcionaria em dev via proxy do Vite, que reescreve same-origin).
- **Alternatives considered**: Nenhuma — é um requisito técnico direto do modelo de CORS do browser, não uma escolha de design.

## R10: Escolha de backend de coleta/visualização — Jaeger para a primeira entrega, Tempo como caminho de evolução documentado

O spec deixa a ferramenta explicitamente como decisão de plano (`Assumptions`). O projeto já roda MinIO (S3-compatível) via `docker-compose.yml`, o que tornaria Grafana Tempo (que usa armazenamento de objeto) uma opção natural a médio prazo, mas exige also implantar Grafana para visualização — mais peças móveis para uma primeira entrega.

- **Decision**: Implantar Jaeger (`jaegertracing/all-in-one`) como backend de armazenamento/visualização inicial, atrás do OTel Collector (R5), como novo(s) serviço(s) no `docker-compose.yml`. Manter a exportação sempre via OTLP (não acoplar nenhum serviço da aplicação diretamente ao SDK/API do Jaeger), para que trocar Jaeger por Tempo, Grafana Cloud, Honeycomb ou outro backend compatível com OTLP no futuro seja apenas uma mudança de configuração do Collector, não de código de aplicação.
- **Rationale**: Jaeger all-in-one sobe com um único container e UI própria embutida (porta padrão 16686), suficiente para cumprir SC-001 (localizar o registro completo em <2min) sem exigir Grafana adicional nesta entrega.
- **Alternatives considered**: Grafana Tempo + Grafana + MinIO como backend de armazenamento — mais alinhado ao longo prazo (reaproveita o MinIO já existente) mas adiado para uma iteração futura por adicionar mais componentes de infraestrutura do que o necessário para validar o valor da feature agora; documentado aqui para não perder a decisão.

## R11: Gap na Constitution — "Technology Standards" não lista uma stack de observability

`.specify/memory/constitution.md` trava a stack tecnológica ("Deviations MUST be proposed as constitution amendments before implementation") mas não menciona nenhuma ferramenta de tracing/observabilidade hoje.

- **Decision**: Tratar a introdução do OTel Collector + Jaeger como uma adição aditiva à seção "Technology Standards" (não uma mudança de framework/linguagem já padronizado), proposta como amendment MINOR (nova infraestrutura, nenhum princípio removido/redefinido) antes ou junto da implementação — ver Constitution Check em `plan.md`.
- **Rationale**: Cumpre a política de governança já definida sem bloquear a feature; a mudança é estritamente aditiva (novos containers de observabilidade), não conflita com nenhum princípio existente.
- **Alternatives considered**: Implementar sem atualizar a constitution — rejeitado, viola a política de governança do próprio projeto ("Deviations MUST be proposed as constitution amendments before implementation").

## R12: Riscos observados fora do escopo direto desta feature (não corrigidos aqui)

- `frontend/Dockerfile` usa `node:18-alpine` enquanto a CI usa Node 22 (`frontend-ci.yaml`) — divergência pré-existente. Os pacotes `@opentelemetry/*` para Web funcionam em Node 18+, então não bloqueia esta feature, mas fica registrado como risco de build caso alguma dependência futura exija Node mais novo.
- `layout-service` e `camunda-workers` não têm job de deploy em `.github/workflows/ci.yaml` hoje — a instrumentação desses dois serviços cobre o ambiente de desenvolvimento/docker-compose desde já; estender o pipeline de deploy para eles é um gap pré-existente, não introduzido nem obrigatoriamente resolvido por esta feature.
- `backend-com` declara `structlog` como dependência não utilizada — não removida nem adotada nesta feature (fora de escopo), apenas observada.

## Resumo de decisões

| # | Decisão | Componentes afetados |
|---|---|---|
| R1 | `layout-service` e `camunda-workers` são pontos de instrumentação próprios | Escopo do plano |
| R2 | SDKs OTel por tipo de serviço, bootstrap central em `shared/docuparse_observability` | Todos os serviços |
| R3 | Contexto de trace propagado ao Zeebe via variável de processo + Span Links | `camunda-workers`, `backend-core` (start do processo) |
| R4 | Campo `trace_context` no schema base de evento + Span Links no consumo | `contracts/events/schemas.py`, `shared/docuparse_events`, todos os `*_event_worker.py` |
| R5 | Tail sampling no OTel Collector (retém 100% dos erros) | `docker-compose.yml` (novo serviço `otel-collector`) |
| R6 | `BatchSpanProcessor` + exporter fail-open | `shared/docuparse_observability/tracing.py` |
| R7 | Processor central de redação de dados sensíveis | `shared/docuparse_observability/tracing.py` |
| R8 | `log_event()` passa a anexar `trace_id`/`span_id` | `shared/docuparse_observability/__init__.py` |
| R9 | CORS libera `traceparent`/`tracestate` | `backend-com`, `backend-core` |
| R10 | Jaeger (via OTel Collector) como backend inicial | `docker-compose.yml` |
| R11 | Amendment à Constitution (Technology Standards) | `.specify/memory/constitution.md` |
| R12 | Riscos pré-existentes registrados, não corrigidos nesta feature | — |
