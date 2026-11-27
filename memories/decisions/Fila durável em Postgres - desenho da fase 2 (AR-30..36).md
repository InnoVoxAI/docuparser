---
title: Fila durável em Postgres - desenho da fase 2 (AR-30..36)
type: note
permalink: docuparser/decisions/fila-duravel-em-postgres-desenho-da-fase-2-ar-30..36
tags:
- arquitetura
- fila
- fase-2
- decisao
---

Detalhamento em `docs/architecture-review-2026-11/tasks.md` (fase 2, em `dev` desde o #85), 2026-11-27. AR-30 implementado (ver abaixo).

## Decisões do usuário
- [decisao] Tabela nova `ProcessingJob` num app novo `jobqueue` em SHARED_APPS (schema public), com `tenant_schema` e `document_id` sem FK. `OrchestrationRun`/`TaskExecution` continuam como auditoria e dashboard; o job guarda o `run_id`.
- [decisao] Tabela própria com `SELECT … FOR UPDATE SKIP LOCKED`, sem lib (procrastinate exige psycopg3, e o core usa psycopg2; nenhuma lib conhece django-tenants).
- [decisao] Fila global, não por tenant. Idempotência pela constraint única parcial (tenant_schema, document_id, step) com status em queued/running.
- [decisao] Retry transitório: 5 tentativas reagendadas por `run_after` (30 s, 2 min, 8 min, 30 min, ±20% de jitter). Permanente vai direto para failed. Heartbeat perdido conta como tentativa. `erp_dispatch` tem max_attempts=1 e nunca volta para a fila sozinho (heartbeat perdido → ERP_FAILED).
- [decisao] Troca: comando idempotente `enqueue_pending_documents`, que roda uma vez no deploy.
- [decisao] O retry de etapa e o reprocess de OCR enfileiram (202/409). O OCR manual e o langextract manual seguem síncronos.
- [decisao] Duplicado por sha256 com `pg_advisory_xact_lock`, sem índice único (prod pode ter duplicados, e seria migration em tabela existente).

## Achados (dev @ 904ab330)
- [bug] O `@task` nunca levanta exceção: uma falha de OCR ou extração deixa o documento em RECEIVED com o run FAILED. O AR-33 corrige.
- [bug] O duplicado é detectado por `original_filename`, check-then-insert, sem trava.
- [fato] `submit_document_langextract` é código morto. `retry_step` confere o run RUNNING sem trava.

## AR-30 implementado (2026-11-27, `feat/ar-30-processingjob`)
- [fato] App `backend-core/jobqueue` em SHARED_APPS: `models.py` (`ProcessingJob`), `policy.py` (`StepPolicy`, `STEP_POLICIES`, `policy_for`) e `migrations/0001_initial.py`, gerada por makemigrations e sem dependências. Nenhuma migration existente mudou. **Não rodada em hml**: sobe com a tag da fase 2.
- [decisao] Choices em minúsculas (`queued`/`running`/`done`/`failed`/`cancelled`; `ocr`/`extraction`/`erp_dispatch`), porque o worker usa SQL cru. O `OrchestrationRun` usa maiúsculas.
- [decisao] Nomes que o AR-31 e o AR-32 usam: unique parcial `jobqueue_one_active_job_per_step` (alvo do ON CONFLICT), índice de claim `jobqueue_claim_idx` `(run_after, id) WHERE status='queued'` e índice de recuperação **parcial** `jobqueue_recovery_idx` `(heartbeat_at) WHERE status='running'`.
- [decisao] CheckConstraints no banco: `jobqueue_valid_step`, `jobqueue_valid_status` e `jobqueue_attempts_within_max`. Ou seja, o claim (`attempts+1`) nunca pode passar de `max_attempts`.
- [decisao] `max_attempts` sem default: o enqueue copia de `policy_for(step)`.
- [bug] O `pytest.ini` do core só coleta classes `Test*`. Cinco classes `tenant_db` simples nunca rodaram (TenantIsolationTests, TenantSchemaIsolationTests, NewTenantGlobalCatalogRegressionTests, CatalogGlobalityTests, CheckCatalogDivergenceTenantTests). Não corrigido.
- [fato] Testes: `jobqueue/tests/test_models.py`, 15 passed contra Postgres (inclui a tabela ausente no schema de um tenant real).

## Plano
Ordem: AR-30 → (AR-31 ∥ AR-32) → AR-33 → AR-34 → AR-35; AR-36 no fim. Flag `DOCUPARSE_PROCESSING_MODE=thread|queue` até o AR-34, que remove o pool, libera gunicorn com mais de 1 worker e muda o CronJob do sweeper para 30 min / `--older-than-minutes 60`. O AR-35 cria `docuparser-core-worker` (args worker, liveness por exec em `/tmp/worker-alive`, grace de 360 s, resources iguais ao web do AR-05) em `docuparser-core/`, para pegar o sed da tag.

- relates_to [[Revisão de arquitetura 2026-11]]
- relates_to [[Retry classificado no orquestrador (AR-27)]]
- relates_to [[Bug conhecido: threads de fundo perdem a conexão quando o Postgres reinicia]]
