---
title: 'Bug conhecido: threads de fundo perdem a conexão quando o Postgres reinicia'
type: note
permalink: docuparser/reference/bug-conhecido-threads-de-fundo-perdem-a-conexao-quando-o-postgres-reinicia
tags:
- bug
- backend-core
- postgres
- background-threads
- incident
---

## Incidente (hml, 24–25/11/2026)

Depois do deploy do Postgres com pgvector no k3s (24/11 19:11), o core parou de
processar documentos, sem nenhum erro no log. O frontend ficou consultando o status
para sempre. As telas continuavam funcionando.

## Causa

- O processamento roda num `ThreadPoolExecutor` em
  `backend-core/documents/services/processing_queue.py`.
- O Django só renova conexões no ciclo de uma requisição HTTP. As threads do pool
  ficavam com a conexão aberta na primeira tarefa e, depois do restart do Postgres,
  toda tarefa falhava em `orchestration_run` → `writer.start` (gravação do run).
- O `Future` devolvido por `_executor.submit` era descartado e a exceção sumia.

## Correção (branch `fix/background-db-connections`)

- `_with_fresh_connection` envolve toda tarefa do pool: `close_old_connections()`
  antes e `connection.close()` no `finally`.
- `_run_document_processing_safely`: `logger.exception("processing_queue_failed …
  last_step=…")` e marca o documento `RECEIVED → OCR_FAILED` com
  `metadata.processing_error`. Não mexe em documento que já avançou.
- `ocr_processor.reset_step()` no início de cada tarefa, para o `last_step` não
  herdar a etapa da tarefa anterior da mesma thread.
- `_run_ocr_safely` (thread nova por chamada) fecha a conexão no `finally`.
- `erp_import/background._run` chama `close_old_connections()` no início.
- Testes: `documents/tests/test_processing_queue.py`.

## Regra para código novo

Toda thread de fundo que usa o ORM precisa: `close_old_connections()` no início,
`connection.close()` no fim e `try/except` com `logger.exception`. Não depender
do `Future` do executor.

## Pendências (fora do código)

- Depois do restart, documentos que ficaram em RECEIVED não voltam sozinhos para
  a fila: é preciso reprocessar ou reenviar.
- Proposta ainda não feita: varredura periódica que marca documentos parados em
  RECEIVED há mais de N minutos.
- Nenhum deployment roda `manage.py consume_events`, então os eventos
  `ocr.completed` publicados no Redis não são consumidos.

Relacionado: [[Bugs pré-existentes na suíte de testes (encontrados na impl. 018)]].
