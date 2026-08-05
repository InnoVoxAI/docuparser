# Contrato: Convenções de Rastreamento entre Serviços

Este documento é o contrato que todo serviço instrumentado (`backend-com`, `backend-core`, `backend-ocr`, `langextract-service`, `layout-service`, `camunda-workers`, `frontend`) DEVE seguir para que os traces sejam consistentes e correlacionáveis entre si. Ver [[../research.md]] e [[../data-model.md]] para as decisões que motivam cada regra.

## 1. Bootstrap único por serviço

Todo serviço Python DEVE chamar `shared.docuparse_observability.tracing.configure_tracing(service_name: str)` uma única vez, no início do processo (antes de qualquer request ser aceito), passando o nome canônico do serviço (`backend-com`, `backend-core`, `backend-ocr`, `langextract-service`, `layout-service`, `camunda-workers`). Nenhum serviço DEVE instanciar seu próprio `TracerProvider`/exporter diretamente.

O `frontend` DEVE inicializar o SDK Web equivalente (`@opentelemetry/sdk-trace-web`) em um módulo único (`src/shared/lib/tracing.ts`), chamado uma vez no bootstrap da aplicação (`main.tsx`), com o mesmo papel do `configure_tracing()` do lado Python.

## 2. Propagação obrigatória via W3C Trace Context em chamadas síncronas

Toda chamada HTTP entre serviços (`backend-com → backend-core`, `backend-core → backend-ocr`, `backend-core → langextract-service`, `camunda-workers → *`, `frontend → backend-core`/`backend-com`) DEVE propagar os cabeçalhos `traceparent` (obrigatório) e `tracestate` (se presente) da chamada de entrada para a(s) chamada(s) de saída. Isso é obtido automaticamente pelas bibliotecas de instrumentação oficiais (`opentelemetry-instrumentation-{fastapi,django,requests,httpx}`) quando o bootstrap (item 1) está em vigor — nenhum código de aplicação deve manipular esses cabeçalhos manualmente.

## 3. Propagação obrigatória via `trace_context` em fronteiras assíncronas

Toda publicação de evento (`shared.docuparse_events`) e todo início de processo Zeebe (`camunda-workers`/`scripts/start_process.py`) DEVE serializar o contexto de trace ativo (via `opentelemetry.propagate.inject()`) no campo `trace_context` do evento (`contracts/events/schemas.py`, ver [[../data-model.md]]) ou na variável de processo equivalente do Zeebe. Todo consumidor de evento (`*_event_worker.py`) e todo `job handler` do Zeebe (`camunda-workers/src/workers/*.py`) DEVE extrair esse contexto e associá-lo ao novo span via **Span Link** (nunca via parent-child direto — ver [[../research.md]] R3/R4).

Se `trace_context` estiver ausente (evento publicado por um caminho não instrumentado, ou consumidor de uma versão anterior à feature), o consumidor DEVE iniciar um trace novo, desconectado, em vez de falhar — consistente com o Edge Case do spec sobre quebra de propagação.

## 4. Atributos de span — allowlist/denylist

Nenhum serviço DEVE adicionar aos spans qualquer atributo fora da allowlist definida em [[../data-model.md]] (`http.method`, `http.route`, `http.status_code`, `net.peer.name`, `messaging.*`, `zeebe.*`, `tenant_id`, `document_id`, `correlation_id`, `error.type`, `error.message`). Em particular, é PROIBIDO incluir conteúdo de documento, dado pessoal extraído, corpo de requisição/resposta HTTP, ou qualquer credencial/token como atributo de span — mesmo temporariamente para debug. O processor central de redação (`configure_tracing()`) atua como rede de segurança, mas não substitui a responsabilidade do código de não tentar capturar esses dados em primeiro lugar.

## 5. Nomenclatura de spans

Nomes de span DEVEM seguir o padrão de baixa cardinalidade das convenções semânticas do OpenTelemetry (ex.: `{METHOD} {route_template}` para HTTP, nunca a URL completa com IDs interpolados; `zeebe.job.{job_type}` para jobs Zeebe; `redis.{command} {stream}` para operações de stream).

## 6. Resiliência — a aplicação nunca aguarda a infraestrutura de tracing

Nenhum serviço DEVE usar `SimpleSpanProcessor` (exportação síncrona bloqueante) em produção — apenas `BatchSpanProcessor`, com timeout de exportação curto configurado centralmente em `configure_tracing()`. Falha ou indisponibilidade do OTel Collector NUNCA deve propagar como erro de requisição de usuário (FR-008).

## 7. CORS para propagação a partir do frontend

`backend-com` e `backend-core` DEVEM incluir `traceparent`/`tracestate` na lista de cabeçalhos CORS permitidos (ver [[../research.md]] R9), para que o SDK Web do frontend consiga propagar contexto de trace em chamadas cross-origin em produção.
