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

## Fase 2: varredura (mesma branch)

- `documents/services/processing_recovery.py`:
  - `mark_received_document_failed`, usada também pela fila;
  - `sweep_stuck_processing`, que fecha como FAILED os runs RUNNING mais antigos que
    o limite e marca OCR_FAILED (`error_type=StuckInQueue`) os documentos em
    RECEIVED com `updated_at` mais antigo que o limite e sem run RUNNING recente.
- Comando `manage.py sweep_stuck_documents [--older-than-minutes 30] [--tenant]
  [--dry-run]`. Percorre os tenants ativos e sai com código 1 se algum falhar.
- Por que fechar os runs: `retry_step` (process_dashboard) recusa o retry
  se existe um run RUNNING. Um run órfão bloqueava o retry daquele documento para
  sempre.
- `CONN_HEALTH_CHECKS = True` em `core/settings.py`. Só vale para o ciclo HTTP.
- O probe `/ready` não passou a checar o banco: este bug não seria detectado por
  ele (cada requisição abre uma conexão nova), e o `/diagnostics` já testa o banco.

## Regra para código novo

Toda thread de fundo que usa o ORM precisa: `close_old_connections()` no início,
`connection.close()` no fim e `try/except` com `logger.exception`. Não depender
do `Future` do executor.

## Pendências (fora do código)

- Depois do restart, documentos que ficaram em RECEIVED não voltam sozinhos para
  a fila: é preciso reprocessar ou reenviar.
- O CronJob da varredura (ver acima) precisa ser criado no repositório de manifests
  do k3s. O YAML de exemplo está em `docuparse-project/docs/TECHNICAL.md`.
- O pipeline por eventos (incluindo o `consume_events`) foi removido. Ver
  [[Remoção do pipeline por eventos e do Camunda]].

Relacionado: [[Bugs pré-existentes na suíte de testes (encontrados na impl. 018)]].
