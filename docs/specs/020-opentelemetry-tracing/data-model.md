# Data Model: Rastreamento Distribuído (OpenTelemetry) entre Serviços

## Overview

Esta feature não introduz uma nova tabela de banco de dados — o "dado" que ela cria é telemetria (traces/spans), que vive na ferramenta de coleta (ver [[research.md]] R10: Jaeger via OTel Collector), não no PostgreSQL de `backend-core`. A única mudança de schema persistente é um campo novo, opcional, no schema de evento compartilhado (`contracts/events/schemas.py`), usado para propagar contexto de trace através do barramento de eventos (R4).

## Entidades (conceituais — modelo de dados do OpenTelemetry, não tabelas próprias)

### Trace

Uma requisição de ponta a ponta. Identificado por um `trace_id` (128 bits, gerado pelo SDK OTel no primeiro serviço tocado). Não é uma entidade persistida pela aplicação — vive inteiramente na ferramenta de coleta/visualização.

| Atributo | Origem | Notas |
|---|---|---|
| `trace_id` | Gerado pelo SDK OTel no ponto de entrada (frontend, ou o primeiro backend a receber a requisição sem contexto de entrada) | Propagado via cabeçalho HTTP `traceparent` (W3C Trace Context) entre chamadas síncronas, e via `trace_context` (ver abaixo) entre chamadas assíncronas. |
| Resource attributes | `service.name`, `service.version`, `deployment.environment` | Atribuídos por `configure_tracing()` (`shared/docuparse_observability/tracing.py`, novo — ver [[research.md]] R2) a partir de variáveis de ambiente por serviço. |
| Status geral | Derivado (sucesso se nenhum span com status de erro; erro caso contrário) | Não é um campo armazenado pela aplicação — calculado pela ferramenta de visualização a partir dos spans. |

### Span (Etapa)

Unidade de trabalho dentro de um trace, associada a uma operação específica de um serviço.

| Atributo | Notas |
|---|---|
| `span_id` | Gerado pelo SDK ao entrar em cada operação instrumentada (request HTTP recebido, chamada HTTP de saída, comando Redis, job Zeebe). |
| `parent_span_id` / `links` | `parent_span_id` para chamadas síncronas dentro do mesmo processo/cadeia de requisição; `links` (não parent-child) para fronteiras assíncronas — fila de eventos e execução de job Zeebe (ver [[research.md]] R3, R4). |
| `name` | Nome da operação (ex.: `POST /api/ocr/events/document-received`, `redis.xadd`, `zeebe.job.ocr.process`). |
| `start_time` / `duration` | Usados para identificar gargalos (História 2 do spec). |
| `status` | `OK` / `ERROR` (com `status.message` quando erro). |
| `attributes` | Metadados técnicos permitidos (ver allowlist abaixo) — nunca conteúdo de documento ou dado pessoal (FR-006). |

**Allowlist de atributos permitidos** (aplicada pelo processor central, [[research.md]] R7):

- `http.method`, `http.route`, `http.status_code`, `net.peer.name`
- `messaging.system` (`redis`), `messaging.destination` (nome do stream)
- `zeebe.job.type`, `zeebe.process.instance.key`
- `tenant_id`, `document_id`, `correlation_id` (já usados hoje em `log_event()`, reaproveitados como atributos de span)
- `error.type`, `error.message` (sem stack trace completo com paths de sistema, quando evitável)

**Denylist explícita** (removida/mascarada mesmo se alguma biblioteca tentar capturar): `http.request.body`, `http.response.body`, `Authorization`, qualquer atributo com nome terminado em `_token`, `_secret`, `_password`, e qualquer atributo cujo valor contenha texto de documento extraído.

### Falha de comunicação (representada como span de erro, não entidade própria)

Uma chamada entre serviços que falha (timeout, indisponibilidade, resposta inesperada) é um **span com `status = ERROR`**, cujos atributos `net.peer.name`/`http.route` identificam origem/destino, e `error.type` identifica a natureza (`timeout`, `connection_refused`, `http_5xx`, etc.). Não requer uma tabela ou schema separado — é o próprio span de saída (client span) da chamada HTTP/Redis/gRPC que falhou.

### Erro de aplicação (representado como span de erro + evento de exceção)

Uma exceção não tratada durante o processamento de uma etapa é registrada via `span.record_exception()` (API padrão do OTel), que anexa tipo, mensagem e stack trace ao span ativo como um "span event", e marca `span.status = ERROR`. Combinado com R8 ([[research.md]]), o mesmo `trace_id`/`span_id` passam a acompanhar o log de erro já emitido por `log_event()`, permitindo saltar de um log de erro para o trace completo.

## Mudança de schema concreta

### `contracts/events/schemas.py` — campo novo no schema base de evento

| Campo | Tipo | Notas |
|---|---|---|
| `trace_context` | `dict[str, str] \| None`, default `None` | Novo campo opcional no schema base de evento (ao lado do `correlation_id: UUID` já existente). Populado via `opentelemetry.propagate.inject()` no momento da publicação (dentro de `shared/docuparse_events`); consumido via `opentelemetry.propagate.extract()` em cada `*_event_worker.py` para criar um Span Link (ver [[research.md]] R4). |

**Compatibilidade**: campo opcional com default `None` — eventos publicados antes desta feature (ou por qualquer publisher ainda não instrumentado) continuam válidos; consumidores tratam `trace_context is None` iniciando um trace novo e desconectado (mesmo comportamento do Edge Case "etapa não propaga o identificador", que a spec já pede para não derrubar a requisição).

**Relação com `correlation_id`**: os dois campos coexistem e servem propósitos diferentes (ver [[research.md]] R4) — `correlation_id` é a chave de negócio estável do documento inteiro (já usada em `Document`/eventos), `trace_context` é o carrier técnico do OTel para aquele salto específico. Nenhuma migração de dado é necessária para `correlation_id`.

## Configuração (não é "dado" de negócio, mas é estado versionado necessário)

| Variável de ambiente | Onde é usada | Notas |
|---|---|---|
| `OTEL_SERVICE_NAME` | Todos os serviços | Nome usado no atributo de resource `service.name` (ex.: `backend-core`, `backend-ocr`, `camunda-workers`). |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Todos os serviços | Aponta para o novo serviço `otel-collector` no `docker-compose.yml` (ex.: `http://otel-collector:4317`). |
| `DEPLOYMENT_ENVIRONMENT` | Todos os serviços | Popula `deployment.environment` (dev/staging/production) — usado para filtrar investigação por ambiente (FR-010). |
| `OTEL_TRACES_SAMPLER_ARG` | Apenas relevante no Collector (tail sampling), não por serviço — ver [[research.md]] R5 | Configuração do `tailsamplingprocessor`, não uma env var de aplicação. |
