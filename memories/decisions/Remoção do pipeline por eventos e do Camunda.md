---
title: Remoção do pipeline por eventos e do Camunda
type: decision
permalink: docuparser/decisions/remocao-do-pipeline-por-eventos-e-do-camunda
tags:
- arquitetura
- eventos
- camunda
- processamento
---

## Decisão (2026-11-26)

O processamento de documentos roda **só** dentro do backend-core: upload → HTTP para
backend-ocr e langextract-service, num pool de threads, com o orquestrador leve
(`docuparse_orchestrator`, POC do commit `90ebb955b`, ago/2026) registrando runs e tasks.
Removidos (branch `chore/remove-event-pipeline-and-camunda`):

- `consume_events` + `event_stream_worker` do core e os consumers `ocr.completed`,
  `ocr.failed` e `extraction.completed`;
- workers de eventos do backend-ocr (`ocr_event_worker`), do layout-service e do
  langextract-service (mais o `backend_core_client` dele);
- serviços do compose `backend-core-events`, `backend-ocr-worker`, `layout-worker`,
  `langextract-worker` e todo o Camunda (`camunda-workers/`, `bpmn/`, zeebe, operate,
  tasklist, elasticsearch), além das dependências Camunda do backend-com.

## Por quê

- Havia três gerações de arquitetura empilhadas: eventos (mai/2026), pipeline interno
  via HTTP (jun/2026, a que de fato roda) e o orquestrador leve (ago/2026).
  `docs/orchestrator-poc-vs-camunda.md` já concluía que o Camunda não é necessário.
- Em hml e prod, `DOCUPARSE_OCR_WORKER_ENABLED=true` fazia o backend-ocr **refazer o OCR**
  de todo upload (custo de OpenRouter e erros 429). Com `START_AT_LATEST=False`, a cada
  restart ele refazia o OCR do stream inteiro, gravando na mesma chave de storage do core
  (`document_ocr_raw_text_key`) e podendo sobrescrever o texto que o core usou.
- Ligar o `consume_events` não funcionaria: os consumers não trocam o schema do tenant,
  `document.received` sempre daria `DuplicateDocumentError` (o HTTP já criou o
  documento) e `ocr.completed` faria o status voltar de VALIDATION_PENDING para
  OCR_COMPLETED.

## O que ficou

- `consume_document_received`: usado pelo endpoint HTTP `/api/ocr/events/document-received`.
- `consume_erp_integration_requested`, `consume_erp_sent` e `consume_erp_failed`: o fluxo
  do ERP usa os eventos como mensagens **em processo** (`submit_erp_dispatch`,
  `erp_export.outcome.apply_outcome`) e também os publica no barramento.
- O backend-com ainda publica `document.received` no Redis; ninguém consome.

## Segunda etapa (mesma branch)

- Removidas as DLQs: `dlq_inspector`, os comandos `inspect_dlq` e `requeue_dlq`, os endpoints
  `/api/ocr/operations/dlq/*`, `publish_dead_letter` e `sleep_interval` de
  `shared/docuparse_events`, e a tela **Operações** do frontend (`modules/operations`).
  A permissão `operations.access` **continua**: ela libera o dashboard de processos e o retry
  de etapas (`document-retry-step`). Os testes de RBAC passaram a usar esse endpoint.
- Removido o `layout-service` inteiro. A classificação usada é `backend-core/models/classifier.py`.
- Removidos os docs da biblioteca "atoms" (`docs/backend-com/`). O `backend-com/README.md`
  foi reescrito, porque o `pyproject.toml` exige o arquivo (`readme = "README.md"`).

## Pontos de atenção

- Com `SuperlogicaMode.DISABLED`, `publish_erp_integration_requested` só publica no
  barramento e não chama `submit_erp_dispatch`, então o documento fica em
  ERP_INTEGRATION_REQUESTED. **É intencional** (decisão do usuário em 2026-11-26): a
  integração com o Superlógica está em desenvolvimento e já existe uma chave de produção.
  Nada pode disparar um envio por engano. Não "consertar" isso.

Relacionado: [[Bug conhecido: threads de fundo perdem a conexão quando o Postgres reinicia]].
