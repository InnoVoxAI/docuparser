# Quickstart: Validando o Rastreamento Distribuído Localmente

## 1. Subir o stack com o Collector e o Jaeger

```bash
cd docuparse-project
docker compose up -d otel-collector jaeger postgres redis minio minio-setup \
  backend-core backend-com backend-ocr langextract-service layout-service frontend
```

(`otel-collector` e `jaeger` são os dois novos serviços introduzidos por esta feature — ver [[research.md]] R5/R10. Para incluir o caminho assíncrono completo, adicionar `--profile async-workers` e, para o caminho de orquestração, `--profile camunda`.)

## 2. Disparar uma requisição de ponta a ponta

Enviar um documento de teste através do fluxo já existente (upload via `backend-com`, que dispara `document.received` para `backend-core`, que por sua vez chama `backend-ocr` e, dependendo do fluxo, `langextract-service`/`layout-service`):

```bash
./run_script.sh curl -X POST http://localhost:8070/api/documents/upload \
  -F "file=@./docs/specs/020-opentelemetry-tracing/quickstart-sample.pdf" \
  -H "Authorization: Bearer <token de teste>"
```

Anotar o `trace_id`/`traceparent` retornado (se exposto em um cabeçalho de resposta) ou o `correlation_id` do documento criado.

## 3. Localizar o trace no Jaeger

1. Abrir `http://localhost:16686` (UI padrão do Jaeger all-in-one).
2. Selecionar o serviço `backend-com` (ponto de entrada) e buscar pelo `trace_id` conhecido, ou pesquisar pelas últimas requisições recentes.
3. Confirmar (mapeando para as Histórias do spec):
   - **História 1**: o trace mostra spans de `backend-com`, `backend-core`, `backend-ocr` (e `langextract-service`/`layout-service`, se aplicável) em ordem cronológica.
   - **História 2**: cada span exibe sua duração individual; é possível somar/comparar tempos por serviço.
   - **História 3**: derrubar temporariamente `backend-ocr` (`docker compose stop backend-ocr`) antes de repetir o passo 2 e confirmar que o span da chamada `backend-core → backend-ocr` aparece com status de erro, indicando origem/destino e natureza da falha (timeout/conexão recusada).
   - **História 4**: forçar um erro de aplicação (ex.: enviar um payload inválido que dispare uma exceção não tratada em algum dos serviços) e confirmar que o span correspondente aparece com status `ERROR` e um evento de exceção anexado, sem nenhum conteúdo de documento visível nos atributos.

## 4. Validar resiliência (FR-008)

```bash
docker compose stop otel-collector
# repetir o passo 2 — a requisição de upload deve continuar funcionando normalmente,
# sem aumento perceptível de latência e sem erro 5xx causado pela ausência do Collector.
docker compose start otel-collector
```

## 5. Validar ausência de dados sensíveis (FR-006/SC-005)

No Jaeger, inspecionar os atributos de qualquer span do fluxo testado e confirmar que nenhum deles contém texto extraído do documento, dados pessoais, tokens ou cabeçalho `Authorization` — apenas os atributos da allowlist (ver [[data-model.md]]).

## 6. Rodando os testes automatizados relevantes

```bash
# Exemplo para backend-core (ajustar por serviço via run_script.sh, conforme CLAUDE.md)
./run_script.sh backend-core pytest documents/tests/test_tracing_propagation.py -v
```

Os testes de propagação usam `opentelemetry.sdk.trace.export.InMemorySpanExporter` (sem depender de um Collector/Jaeger real) para verificar que: (a) um span de saída propaga `traceparent` para o serviço chamado; (b) um evento publicado carrega `trace_context`; (c) span de erro é gerado quando a chamada de saída falha.
