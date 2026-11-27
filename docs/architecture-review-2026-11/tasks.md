# Backlog acionável

Formato: **ID · título**. Cada tarefa traz finding de origem, arquivos, critério de aceite e
dependências. As linhas citadas são de 2026-11-26 e precisam ser conferidas.
Estado de cada tarefa: [work_in_progress.md](work_in_progress.md).
⚠️ = toca prod, credenciais ou migrations: **confirmar com o usuário antes**.

---

## Fase 0 — Segurança e produção imediata

### AR-01 · Fechar `POST /api/ocr/process`
- **Origem:** A1. **Arquivos:** `backend-core/documents/views.py:183+`, `documents/urls.py:50`.
- **Fazer:** verificar se algum cliente usa a rota (frontend: `grep -rn "ocr/process\b"`;
  testes; backend-com). Se ninguém usar, remover. Se alguém usar, converter para view DRF
  com autenticação e permissão.
- **Aceite:** sem JWT ou token, a rota retorna 401 ou 404. Há um teste cobrindo isso.

### AR-02 · Token interno falhando fechado
- **Origem:** A2. **Arquivos:** `backend-core/documents/views.py:133-156`, `core/settings.py`.
- **Fazer:** fora de `DEBUG` (ou com `DOCUPARSE_ENV in {hml,prod}`), a ausência do token
  impede o boot ou devolve 503. Remover `teste456` da mensagem.
- **Aceite:** existem testes para token ausente em prod e em dev. A mensagem fica limpa.

### AR-03 · `DEBUG=False` em prod ⚠️
- **Origem:** D2. **Arquivo:** `innovox-kubernetes-deployments/apps/docuparser/prod/config-map.yaml:7`
  (repo separado).
- **Fazer:** antes, conferir se algo depende de DEBUG=True (servir estáticos ou media pelo
  Django, `ALLOWED_HOSTS`, mensagens de erro usadas pelo front).
- **Aceite:** prod sobe com DEBUG=False e o smoke test de login, upload e validação passa.

### AR-04 · Servidor de produção no backend-core ⚠️
- **Origem:** D1. **Arquivos:** `backend-core/Dockerfile` (CMD), `backend-core/entrypoint.sh`,
  `backend-core/pyproject.toml`, deployments k8s.
- **Fazer:** adicionar o gunicorn e trocar `runserver` por
  `gunicorn core.wsgi -w N --timeout 120`. **Atenção ao pool de threads em processo:**
  com N workers do gunicorn, há N pools (até a fase 2). Usar `-w 1 --threads 4`, ou
  `--preload` desligado, para não multiplicar processamento enquanto a fila durável não
  existe. Tirar `migrate_schemas` e `seed_data` do caminho de boot e passá-los para um
  initContainer ou Job. O CMD atual do Dockerfile roda `migrate` (só public), divergindo
  do `entrypoint.sh`: unificar.
- **Aceite:** o container sobe com gunicorn em compose e hml. As migrations rodam uma vez
  por deploy.

### AR-05 · Probes e resources no k8s ⚠️
- **Origem:** D3, D9. **Arquivos:** `innovox-kubernetes-deployments/apps/docuparser/{hml,prod}/docuparser-*/deployment.yaml`.
- **Fazer:** descomentar liveness (`/health`) e readiness (`/ready`). Definir requests e
  limits (o backend-ocr precisa de mais memória). Ver também AR-72 (`/ready` real).
- **Aceite:** os pods passam a ficar Ready via probe em hml antes de ir para prod.

### AR-06 · Segredos versionados no repo de deploy ⚠️ (usuário)
- **Origem:** A6, D-06. Agentes **não** editam segredos (guardrail do CLAUDE.md). Apenas
  lembrar o usuário.

### AR-07 · Destino do `/admin/` do Django ⚠️
- **Origem:** levantamento do AR-03 (2026-11-27). **Arquivos:** `backend-core/core/urls.py`,
  `core/settings.py`, `backend-core/Dockerfile`.
- **Contexto:** `/admin/` está exposto em prod (`docuparser-core.innovox.ai/admin/login/`
  responde 200). O CSS só aparece porque a 0.0.15 roda `runserver` com `DEBUG=True`. Não há
  `STATIC_ROOT` nem whitenoise, então sob gunicorn (AR-04) o admin fica sem estilo, com DEBUG
  ligado ou não. Nenhum app registra modelo no admin (só os padrões de `auth` e
  `token_blacklist`), e nada no front ou na documentação aponta para ele. Provavelmente o
  login também falha: o Traefik termina o TLS e não há `SECURE_PROXY_SSL_HEADER` nem
  `CSRF_TRUSTED_ORIGINS` (não testado com POST).
- **Fazer:** decidir com o usuário. (a) Tirar a rota `/admin/` (recomendado se ninguém usa),
  ou (b) mantê-la: whitenoise, `STATIC_ROOT`, `collectstatic` no Dockerfile,
  `SECURE_PROXY_SSL_HEADER` e `CSRF_TRUSTED_ORIGINS`.
- **Aceite:** em (a), `/admin/` responde 404. Em (b), login no admin de hml funciona e com CSS.
- **Decisão (2026-11-27):** opção (a).

---

## Fase 1 — Limpeza e rede de segurança

### AR-10 · Tirar Redis e barramento de onde não é usado
- **Origem:** L1, L4. **Arquivos:** `docker-compose.yml:177,278,323` (core, ocr,
  langextract), `backend-ocr/pyproject.toml`, `langextract-service/pyproject.toml`, setup do
  `RedisInstrumentor` nesses serviços.
- **Fazer:** remover `DOCUPARSE_EVENT_BUS`, `REDIS_URL` e o `depends_on: redis` de ocr e
  langextract. O core e o com publicam: manter até D-04, mas adicionar `MAXLEN ~` no `xadd`
  (`shared/docuparse_events/__init__.py:95`) para as streams pararem de crescer.
- **Aceite:** o compose sobe sem Redis para ocr e langextract, e os testes passam.

### AR-11 · Remover as flags de worker do ConfigMap ⚠️
- **Origem:** L5. `prod/config-map.yaml:14-18` (e hml). Confirmar que a imagem em prod já
  não tem workers (a tag k8s está em 0.0.14; a remoção entrou depois?).

### AR-12 · Contratos e scripts mortos
- **Origem:** L2, L3. Remover `OCRCompletedEvent`, `OCRFailedEvent`, `LayoutClassifiedEvent`,
  `ExtractionCompletedEvent` (com os exemplos JSON e os testes correspondentes),
  `shared/consume_fake_event.py`, `shared/publish_fake_event.py` e `consume`/`consume_entries`
  se nada mais os chamar (`grep` antes).

### AR-13 · Renomear os pyprojects `atoms`
- **Origem:** L4. `backend-ocr/pyproject.toml`, `langextract-service/pyproject.toml`: nome e
  descrição corretos. Regenerar o `uv.lock` de cada um.

### AR-14 · Diretórios e arquivos sem uso
- **Origem:** L6, L7, L8, X4. Apagar do disco `camunda-workers/` e `layout-service/` (só
  `.pyc`, não versionados). Perguntar ao usuário sobre `backend-core/not-used-with-s3/`.
  Remover o volume `docuparse-events` se D-04 = a. Limpar as dependências do
  `pyproject.toml` da raiz. Perguntar sobre `/docuparser/scripts/docker-compose.yml` (OLMOCR).
  Perguntar se `tests/load/simulate_module_load.py` é consertado ou apagado: já estava
  quebrado em `dev` (importa `backend_com` de `backend-com/src`; visto no AR-12).

### AR-15 · Reescrever `docs/architecture.md`
- **Origem:** X1. Usar [findings.md §1](findings.md) e, depois das decisões, o diagrama-alvo.
  Incluir: serviços, portas reais, fluxo do documento, multi-tenancy, storage e
  observabilidade.

### AR-16 · Docs desatualizados
- **Origem:** X2, X3, L10. `docuparse-project/README.md`, `docs/TECHNICAL.md`,
  `.env.example:73-76`, `docs/langextract_integration_map.md`, `docs/fixplans/*` (marcar como
  histórico ou apagar), o texto sobre Zeebe em `tracing.py:135`, o comentário de DLQ em
  `frontend/vitest.config.ts:32` e o item de Operações em `frontend/TYPESCRIPT_MIGRATION.md:421`.

### AR-17 · Tabela única de env vars
- **Origem:** D10. `docs/configuration.md`, com cada variável por serviço, default, onde é
  definida (compose, ConfigMap, Secret) e se é obrigatória em prod.

### AR-20 · CI de backend
- **Origem:** D4. Novo workflow (ou job no `ci.yaml`) com matriz por serviço: `uv sync`,
  `ruff check`, `pytest`. Para o core: Postgres como service container e
  `python manage.py makemigrations --check --dry-run`. Usar `run_script.sh` como referência
  das env vars.
- **Aceite:** um PR que quebre um teste de backend falha no CI.

### AR-21 · O build de imagem depende dos testes
- O build e o deploy só rodam depois do AR-20 verde.

### AR-22 · Tags imutáveis
- **Origem:** D5. Tag = `<versão>-<sha curto>`. O deploy grava essa tag no repo k8s. Nunca
  republicar a mesma tag.

### AR-23 · Corrigir `ci.yaml:18`
- **Origem:** L9. Referência a `steps.check_version.outputs.SKIP`, que não existe.

### AR-24 · Conexões nas threads restantes
- **Origem:** P6. `processing_queue.py`: envolver `_run_erp_dispatch` e
  `_run_langextract_safely` com `_with_fresh_connection`. Escrever um teste no padrão de
  `documents/tests/test_processing_queue.py`.

### AR-25 · Remover `start_document_ocr_thread`
- **Origem:** P7. `ocr_processor.py:447-457`, sem chamadores (confirmar com grep).

### AR-26 · Ampliar o sweeper e agendá-lo (paliativo até a fase 2)
- **Origem:** P2. `processing_recovery.py`: cobrir extração presa (OCR_COMPLETED +
  `metadata.extraction.state="running"`) e runs RUNNING órfãos de qualquer etapa. Agendar
  via CronJob (ver AR-70).
- **Feito (código):** extração presa em qualquer status vira `state="failed"`
  (`StuckInQueue`), com status inalterado; um só limite (30 min); comando idempotente. Falta o
  CronJob (AR-70, repo k8s); o manifesto de exemplo está em `docuparse-project/docs/TECHNICAL.md`.

### AR-27 · Retry classificado no orquestrador
- **Origem:** P3. `shared/docuparse_orchestrator/decorators.py`: aceitar `retry_on`
  (exceções transitórias: timeout, conexão, HTTP 429 e 5xx). Erros permanentes não fazem
  retry. Nos clientes (`ocr_client.py`, `langextract_client.py`), levantar exceções tipadas.
- **Aceite:** um teste mostra que um 400 do OCR gera 1 chamada, e um timeout gera 3.

---

## Fase 2 — Processamento durável (D-01 = A, detalhada em 2026-11-27)

### Decisões de desenho (usuário, 2026-11-27)
| Tema | Escolha |
|---|---|
| Estado do job | **Tabela nova** `ProcessingJob`. `OrchestrationRun`/`TaskExecution` continuam como trilha de auditoria e dashboard; o job aponta para o `run_id`. |
| Mecanismo | **Tabela própria + `SELECT … FOR UPDATE SKIP LOCKED`**. Sem lib nova (procrastinate exige psycopg3; nenhuma conhece django-tenants). |
| Escopo | **Fila global no schema `public`** (app em `SHARED_APPS`), com a coluna `tenant_schema`. |
| Retry transitório | **5 tentativas**, reagendadas por `run_after` (sem `sleep` na thread): 30 s, 2 min, 8 min e 30 min, com ±20% de jitter. Erro permanente vai direto para `failed`. Perder o heartbeat conta como tentativa. |
| Documentos em processamento na troca | **Comando de backfill** `enqueue_pending_documents`, idempotente, que roda uma vez no deploy. |
| Rotas síncronas | **Retry de etapa e reprocess de OCR passam para a fila** (202). O OCR manual e o langextract manual continuam síncronos. |
| Bugs incluídos | Status do documento na falha definitiva, e duplicado por sha256. |

### Estado atual (dev @ 904ab330, conferido em 2026-11-27)
- `documents/services/processing_queue.py`: um `ThreadPoolExecutor` (`DOCUPARSE_PROCESSING_WORKERS`, padrão 2).
  `submit_document_processing` roda `ocr_task` e `extraction_task` **na mesma thread**, dentro de um
  `orchestration_run("document_processing")`. `submit_erp_dispatch` chama `consume_erp_integration_requested`.
  `submit_document_langextract` não tem chamador fora dos testes (código morto).
- Quem chama: `views.py:287` (`document_received_event_view`, fora de `atomic`, depois do commit de
  `consume_document_received`) e `erp_publisher.py:89`.
- **Bug:** o `@task` nunca levanta exceção. Quando o OCR ou a extração falham, o documento fica em
  `RECEIVED` com o run `FAILED` (`_mark_document_failed` só roda para erros de antes das tasks).
- **Bug:** o duplicado é detectado por `original_filename` (`event_consumers.py:65`), sem trava. O
  `sha256` vem do backend-com e já tem índice (`models.py:57`), mas não é usado.
- `retry_step` (`process_dashboard.py:576`) é síncrono e confere "já existe run RUNNING" sem trava (`:600`).
- `transition_to` (`models.py:84`) é um `save` simples. Não existe tratamento de SIGTERM em lugar nenhum
  do core. O gunicorn roda com 1 worker por causa do pool (`entrypoint.sh`).
- O comentário em `settings.py:207-208` ("threads renovam a conexão sozinhas") está errado.

### Ordem e dependências
```
AR-30 ──┬─► AR-31 ─┐
        └─► AR-32 ─┴─► AR-33 ─► AR-34 ─► AR-35 (código + k8s) ─► deploy
AR-36: testes de ponta a ponta, escritos depois de AR-34 (cada AR traz os seus testes unitários)
```
AR-31 e AR-32 são independentes entre si. Uma AR por sessão. Até o AR-34, tudo fica atrás da flag
`DOCUPARSE_PROCESSING_MODE=thread|queue` (padrão `thread`), para dar para mergear em `dev` sem mudar o
comportamento.

---

### AR-30 · Modelo `ProcessingJob` e app `jobqueue` ⚠️ (migration nova)
- **Escopo:** um app novo `jobqueue` em `SHARED_APPS` (as tabelas ficam só no `public`). Modelo
  `ProcessingJob`:
  - `id` (BigAutoField), `tenant_schema` (CharField 63), `document_id` (UUID, sem FK: o documento
    fica em outro schema), `step` (`ocr` · `extraction` · `erp_dispatch`), `status` (`queued` ·
    `running` · `done` · `failed` · `cancelled`);
  - `attempts`, `max_attempts`, `run_after`, `locked_by`, `locked_at`, `heartbeat_at`, `finished_at`;
  - `last_error_type`, `last_error_message`, `orchestration_run_id` (CharField 36, o `run_id` do
    orchestrator), `triggered_by`, `payload` (JSON: por exemplo, o evento do ERP), `created_at` e `updated_at`.
  - Restrições: `UniqueConstraint(tenant_schema, document_id, step, condition=status IN (queued, running))`,
    que dá a idempotência do enqueue. Índice parcial `(run_after, id) WHERE status='queued'`
    (claim) e índice `(status, heartbeat_at)` (recuperação).
  - Política por etapa, num dicionário em código (não no banco): `ocr` e `extraction` com
    `max_attempts=5`; `erp_dispatch` com `max_attempts=1` (**nunca reenviar à Superlógica
    automaticamente**).
- **Arquivos:** `backend-core/jobqueue/{__init__,apps,models,policy}.py`,
  `jobqueue/migrations/0001_initial.py` (**só criar**; nenhuma migration existente muda), `core/settings.py`
  (`SHARED_APPS`).
- **Aceite:** `migrate_schemas --shared` cria a tabela só no `public`; `migrate_schemas` (tenants)
  não cria nada; `makemigrations --check` limpo; um segundo job ativo para o mesmo
  `(tenant, documento, etapa)` viola a constraint.
- **Testes:** `jobqueue/tests/test_models.py` (constraint parcial: duplicado ativo falha, e
  duplicado com `done`/`failed` passa; tabela ausente nos schemas de tenant).
- **Depende de:** nada. Perguntar antes de rodar a migration em hml.
- **Como ficou (2026-11-27, `feat/ar-30-processingjob`):** duas mudanças em relação ao escopo acima,
  decididas pelo usuário. O índice de recuperação é **parcial**, `(heartbeat_at) WHERE status='running'`
  (`jobqueue_recovery_idx`). Entraram três CheckConstraints (`jobqueue_valid_step`, `jobqueue_valid_status`
  e `jobqueue_attempts_within_max`), porque o worker escreve por SQL cru. Os valores dos choices são
  minúsculos e `max_attempts` não tem default (o enqueue do AR-31 copia de `policy_for(step)`). Nomes
  para usar no AR-31: a constraint do `ON CONFLICT` é `jobqueue_one_active_job_per_step`, e o índice do
  claim, `jobqueue_claim_idx`.

### AR-31 · `enqueue` transacional e rotas que enfileiram
- **Escopo:**
  - `jobqueue/services.py:enqueue(document, step, *, triggered_by, payload=None, run_after=None)`.
    Lê o tenant de `connection.tenant` e faz `INSERT … ON CONFLICT DO NOTHING` sobre a constraint
    parcial, devolvendo o job ativo existente. Usa a conexão e a transação correntes: o
    `search_path` do django-tenants inclui o `public`, então o job e o documento entram no mesmo commit.
  - `document_received_event_view`: o enqueue de `ocr` vai para **dentro** do `atomic` de
    `consume_document_received` (o job só existe se o documento existir, e vice-versa).
  - `publish_erp_integration_requested`: troca `submit_erp_dispatch` por `enqueue(step="erp_dispatch",
    payload=event)` na mesma transação do `transition_to(ERP_INTEGRATION_REQUESTED)`. Com
    `SuperlogicaMode.DISABLED` continua sem enfileirar (armadilha conhecida, não mudar).
  - `retry_step` e `document_reprocess_ocr_view`: enfileiram e respondem **202** com o `job_id`.
    O `RetryAlreadyRunningError` passa a sair da constraint (job ativo já existe → 409), sem a
    checagem por run RUNNING. O OCR manual (`document_process_ocr_view`) e o langextract manual
    continuam síncronos.
  - Flag `DOCUPARSE_PROCESSING_MODE` (`thread` | `queue`, padrão `thread`): em `thread`, tudo
    segue como hoje. Ela some no AR-34.
- **Arquivos:** `jobqueue/services.py`, `documents/views.py` (`:269-287`, `:373`, `:953`),
  `documents/services/erp_publisher.py:89`, `documents/services/process_dashboard.py:576-600`,
  `core/env.py` (flag), `.env.example`, `docs/TECHNICAL.md`.
- **Aceite:** com a flag em `queue`, um evento document-received gera exatamente 1 documento e 1
  job `ocr` numa transação (um rollback forçado não deixa nenhum dos dois); evento repetido não
  duplica o job; o retry de uma etapa com job ativo responde 409; o frontend aceita o 202 do retry
  e do reprocess (conferir `modules/processes` e a tela do documento: hoje esperam o resultado
  síncrono?).
- **Testes:** `jobqueue/tests/test_enqueue.py`; ajustes em `documents/tests/test_api.py:133`
  (hoje faz patch de `submit_document_processing`), `test_erp_flow.py:129` e
  `test_process_dashboard_api.py`.
- **Depende de:** AR-30.

### AR-32 · Comando `run_worker`
- **Escopo:** `manage.py run_worker [--concurrency 2] [--poll-interval 2] [--steps ocr,extraction,erp_dispatch]`.
  - **Claim** no `public`: `UPDATE … SET status='running', attempts=attempts+1, locked_by=<host:pid:thread>,
    locked_at=now(), heartbeat_at=now() WHERE id = (SELECT id … WHERE status='queued' AND run_after<=now()
    ORDER BY run_after, id FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING …`.
  - **Execução:** `connection.set_tenant(<Tenant de tenant_schema>)` e despacho por `step` para as
    funções de hoje (`process_document_ocr`, `auto_extract_after_ocr`,
    `consume_erp_integration_requested`) via `ocr_task`/`extraction_task` com `max_attempts=1`: quem
    repete é a fila, não o tenacity. O `@task` precisa expor a classe do erro (transitório,
    permanente ou nenhum) ao worker, sem deixar de nunca levantar. Ajustar em
    `shared/docuparse_orchestrator/decorators.py` e em `context.py`, que precisa **retomar** um
    run existente (a etapa `extraction` continua o run aberto pelo `ocr`).
  - **Encadeamento:** o `ocr` concluído com sucesso grava o resultado e enfileira `extraction` na
    mesma transação. A `extraction` não enfileira nada (o documento fica em `VALIDATION_PENDING`).
  - **Resultado:** sucesso → `done`; transitório com `attempts < max_attempts` → `queued` com
    `run_after = now() + backoff(attempts)`; permanente ou esgotado → `failed` (o efeito no documento
    vem no AR-33).
  - **Heartbeat:** uma thread atualiza `heartbeat_at` a cada 15 s para os jobs deste processo. Ela
    também grava `/tmp/worker-alive` (para a liveness do AR-35).
  - **SIGTERM/SIGINT:** para de fazer claims, espera os jobs em curso até
    `DOCUPARSE_WORKER_SHUTDOWN_GRACE` (padrão 330 s: o OCR tem timeout de 300 s,
    `ocr_client.py:43`) e sai com 0. O job que não terminou fica `running` sem heartbeat e
    volta pela recuperação do AR-34.
  - **Conexões:** cada thread usa a própria conexão, com `close_old_connections()` antes de cada
    job e `connection.close()` no fim (mesma regra de `_with_fresh_connection`), e `logger.exception`.
    Uma tabela inexistente (worker subindo antes da migration) gera log e espera, não crash.
  - Entrypoint: novo modo `worker` em `entrypoint.sh` (`uv run python manage.py run_worker "$@"`).
- **Arquivos:** `jobqueue/worker.py`, `jobqueue/backoff.py`, `jobqueue/management/commands/run_worker.py`,
  `shared/docuparse_orchestrator/{decorators,context}.py`, `entrypoint.sh`.
- **Aceite:** dois workers em paralelo nunca pegam o mesmo job; um 503 reagenda com o backoff
  certo; um 400 vai para `failed` com 1 tentativa; com SIGTERM no meio de um job, o worker termina
  o job e sai; o tenant certo é usado (o job do tenant A não enxerga o B).
- **Testes:** `jobqueue/tests/test_worker.py` (claim concorrente com duas conexões em
  `TransactionTestCase`, backoff, classificação do erro, troca de schema, SIGTERM simulado
  com `threading.Event`); `shared/tests` para o decorator e o run retomado.
- **Depende de:** AR-30 (não depende do AR-31: dá para testar enfileirando direto).

### AR-33 · Idempotência por `(documento, etapa)` e efeito no documento
- **Escopo:**
  - **OCR idempotente:** se `raw_text_uri` existe e o objeto está no storage, o job `ocr` não chama
    o backend-ocr; só garante `OCR_COMPLETED` e enfileira `extraction`. Exceção: o reprocess
    explícito, que passa `payload={"force": true}`.
  - **Extração idempotente:** se `metadata.extraction.state == "completed"` e não houver `force`,
    o job termina `done` sem chamar o LLM.
  - **Transições com trava:** `transition_to` ganha uma variante `transition_locked(expected_from=…)`
    com `select_for_update`, e o worker a usa. Se o status mudou (alguém aprovou ou rejeitou no meio
    do caminho), o job termina `cancelled` com motivo, sem sobrescrever.
  - **Falha definitiva** (permanente ou esgotada): `ocr` → documento `OCR_FAILED`, com `error_type`
    e mensagem no metadata; `extraction` → `metadata.extraction.state="failed"`, status inalterado
    (como faz o sweeper); `erp_dispatch` → o caminho de `ERP_FAILED` que já existe. Isso fecha o bug
    do documento parado em `RECEIVED`.
  - **Duplicado por sha256:** em `consume_document_received`, `pg_advisory_xact_lock(hashtext(schema
    || ':' || sha256))` seguido de `exists(sha256=…)`. Quando o sha256 vier vazio, cai para a checagem
    por nome. **Sem índice único** (seria migration em tabela existente, e prod pode já ter
    duplicados). Mudança de comportamento: o mesmo arquivo com outro nome passa a ser duplicado, e
    arquivos diferentes com o mesmo nome deixam de ser. Validar com o usuário na implementação.
- **Arquivos:** `documents/services/ocr_processor.py` (`:64`, `:138`, `:192`, `:270`),
  `documents/models.py:84`, `documents/services/event_consumers.py:55-80`, `jobqueue/worker.py`.
- **Aceite:** um job `ocr` repetido depois do sucesso não chama o backend-ocr (mock com 0
  chamadas); dois envios concorrentes do mesmo arquivo criam 1 documento; um erro permanente deixa
  o documento em `OCR_FAILED`; uma aprovação durante a extração não é sobrescrita.
- **Testes:** `jobqueue/tests/test_idempotency.py`, `documents/tests/test_duplicate_sha256.py`
  (duas conexões), ajustes em `test_classification_pipeline.py`.
- **Depende de:** AR-32.

### AR-34 · Recuperação por heartbeat, backfill e remoção do pool
- **Escopo:**
  - **Reaper** no próprio worker, a cada 30 s: jobs `running` com `heartbeat_at < now() - lease`
    (`DOCUPARSE_JOB_LEASE_SECONDS`, padrão 120) voltam a `queued` com backoff se `attempts <
    max_attempts`; se não, vão a `failed` (`error_type=HeartbeatLost`) com o efeito do AR-33. O
    `erp_dispatch` **nunca** volta para a fila: vai para `failed`/`ERP_FAILED`, porque não se sabe se
    a Superlógica recebeu; o reenvio é o manual que já existe. O reaper usa `SKIP LOCKED`, então
    vários workers não brigam.
  - **Backfill** `manage.py enqueue_pending_documents [--tenant] [--dry-run]`: por tenant, fecha os
    runs `RUNNING` sem job ativo, enfileira `ocr` para documentos `RECEIVED` sem `raw_text_uri` e
    enfileira `extraction` para `metadata.extraction.state="running"` ou para `OCR_COMPLETED` sem
    extração. É idempotente (a constraint barra o repetido) e sai com 1 se algum tenant falhar.
  - **Remover o pool:** sai `processing_queue.py` inteiro (`submit_*`, `_executor`,
    `_with_fresh_connection`, o morto `submit_document_langextract`) e a flag
    `DOCUPARSE_PROCESSING_MODE`. Corrigir o comentário de `settings.py:207-208`. O gunicorn pode
    passar a ter mais de 1 worker (`GUNICORN_WORKERS`, padrão 2), e sai o comentário do
    `entrypoint.sh`.
  - **Sweeper** (`processing_recovery.py`): passa a ignorar documentos com job ativo e runs ligados a
    um job `running`. Continua como defesa para o que ficar fora da fila (documento sem job) e para
    a extração presa. Ganha a métrica e o log "job queued mais antigo há X min" (base do alerta do AR-73).
  - **CronJob do sweeper:** fica, mas a cada 30 min em vez de 10, com `--older-than-minutes 60` (o
    reaper cobre os jobs em 2 min). Reavaliar a remoção depois de um ciclo de release sem
    achados. A mudança é só no `schedule`/`args` de `cronjob.yaml` (branch k8s do AR-35).
- **Arquivos:** `jobqueue/reaper.py`, `jobqueue/management/commands/enqueue_pending_documents.py`,
  remoção de `documents/services/processing_queue.py` e `documents/tests/test_processing_queue.py`
  (os casos úteis migram para `jobqueue/tests`), `documents/services/processing_recovery.py`,
  `core/settings.py`, `entrypoint.sh`, `docs/TECHNICAL.md`, `docs/architecture.md` (AR-15 se ainda
  não estiver feito).
- **Aceite:** um worker morto com `kill -9` no meio de um job → outro worker retoma em até lease
  + 30 s, e `attempts` sobe; `erp_dispatch` órfão vira `ERP_FAILED`, não reenvio; o backfill rodado
  duas vezes enfileira uma vez só; `grep -r submit_document_processing` vazio.
- **Testes:** `jobqueue/tests/test_reaper.py`, `jobqueue/tests/test_backfill.py`, ajustes em
  `documents/tests/test_processing_recovery.py`.
- **Depende de:** AR-31, AR-32 e AR-33.

### AR-35 · Deployment `docuparser-core-worker` (compose e k8s) ⚠️
- **Compose:** serviço `backend-core-worker` com a mesma imagem e `command: ["worker"]`, o mesmo
  env do `backend-core` e `depends_on: backend-core-release (service_completed_successfully)`.
  Sem porta.
- **k8s** (repo `innovox-kubernetes-deployments`, branch nova a partir de `main`, depois de
  `chore/docuparser-probes-resources` e `chore/docuparser-core-release`):
  `apps/docuparser/{hml,prod}/docuparser-core/worker-deployment.yaml`. Fica em `docuparser-core/`
  para pegar o `sed` da tag (`ci/ar-70-cronjob-image-tag` estende o sed a `docuparser-core/*.yaml`).
  - `replicas: 1` (escala depois; a fila aguenta N), mesma imagem, `args: ["worker"]`, `envFrom`
    igual ao do web (`docuparser-config`, `docuparser-secrets` e `docuparser-events-config`,
    enquanto existir). Sem Service nem Ingress e sem initContainer: a migration fica no
    initContainer do web, e o worker espera a tabela (AR-32).
  - `terminationGracePeriodSeconds: 360` (o grace de 330 s do worker + folga). O kubelet manda
    SIGTERM, o worker termina o job em curso e sai.
  - **Probes:** sem HTTP. `livenessProbe` por `exec`, que confere se `/tmp/worker-alive` foi tocado
    há menos de 90 s (`periodSeconds: 30`, `failureThreshold: 3`). `startupProbe` com o mesmo comando
    e até 3 min. Sem readiness (o worker não recebe tráfego).
  - **Resources:** mesmo padrão do AR-05 — `requests: cpu 100m, memory 384Mi`, `limits: memory 1Gi`,
    sem limite de CPU. O worker segura arquivos e o texto do OCR em memória: medir com `kubectl top`
    depois de uma semana.
  - Web: a env `GUNICORN_WORKERS` (2) entra na ConfigMap junto com esta branch.
  - CronJob: ajuste de schedule e args do AR-34.
- **Ordem do deploy** (tag com AR-30..34): (1) o web sobe; o initContainer migra o `public` e cria
  `jobqueue_processingjob`; (2) o worker sobe; (3) roda uma vez `kubectl exec deploy/docuparser-core-worker --
  uv run python manage.py enqueue_pending_documents --dry-run`, depois sem `--dry-run`. Se houver
  documentos em thread no pod web antigo durante o rollout, eles ficam `RECEIVED` sem job e o
  backfill os pega. Smoke: upload → job `ocr` → `extraction` → `VALIDATION_PENDING`;
  `kubectl delete pod` do worker no meio de um OCR → o job volta e termina.
- **Rollback:** voltar a tag do web e escalar o worker a 0. Os jobs ficam no banco; o sweeper
  marca os documentos presos.
- **Arquivos:** `docuparse-project/docker-compose.yml`, os dois `worker-deployment.yaml`, os dois
  `cronjob.yaml`, `config-map.yaml` (hml e prod), `docs/TECHNICAL.md`.
- **Aceite:** YAML válido (pyyaml e `kubectl apply --dry-run=client` se houver acesso); `docker
  compose config` validado no scratchpad com `-p docuparse`; merge simulado com as branches k8s
  pendentes sem conflito.
- **Depende de:** AR-34, AR-05 (`chore/docuparser-probes-resources`) e AR-04 (`chore/docuparser-core-release`).

### AR-36 · Testes de ponta a ponta da fila
- **Escopo:** `jobqueue/tests/test_durable_pipeline.py`, com backend-ocr e langextract mockados, Postgres real e
  dois tenants:
  1. **Restart no meio:** o worker A pega um `ocr`, morre (sem heartbeat), o reaper devolve o
     job, o worker B conclui; o documento chega a `VALIDATION_PENDING` com 1 chamada de OCR
     cobrada por tentativa e nenhuma depois do sucesso.
  2. **Envio duplo:** o mesmo evento document-received duas vezes em paralelo → 1 documento e 1
     job; o mesmo arquivo com outro nome → duplicado.
  3. **Permanente versus transitório:** 400 → 1 chamada e `OCR_FAILED`; 503 ×2 e depois 200 →
     3 chamadas, `done`, com `run_after` respeitando o backoff (com relógio congelado); 503 ×5 →
     `failed`.
  4. **ERP:** heartbeat perdido em `erp_dispatch` → `ERP_FAILED`, 0 reenvios.
  5. **Isolamento:** o job do tenant A nunca lê nem escreve no schema do B.
  6. **Retry manual:** depois de `failed`, o retry do dashboard cria um job novo (`attempts`
     zerado), e o retry duplicado responde 409.
- **Aceite:** a suíte roda no CI do backend (AR-20) em menos de 2 min.
- **Depende de:** AR-31 a AR-34.

### AR-40 · Redis: remover do compose e do k8s
- Só se D-04 = a: junto com o `docuparse_events`. Bloqueada até D-04.

## Fase 3 — Fronteiras

- **AR-50** (D-02) Mover `langextract-service/domain/llm_extractor.py` e os testes para
  `backend-ocr` como `POST /api/v1/extract`.
- **AR-51** O core aponta `LANGEXTRACT_URL` para o backend-ocr (`documents/services/langextract_client.py`).
- **AR-52** Remover o serviço do compose, do k8s e do CI. Atualizar os docs e o CLAUDE.md
  (lista de backends).
- **AR-53** Atualizar as memórias e notas que citam o langextract.
- **AR-54** Cliente OpenRouter único no backend-ocr: semáforo de concorrência, backoff para
  429/5xx com `Retry-After` e circuit breaker (P8).
- **AR-55** Métrica de tokens e custo por tenant e por documento (atributo de span e
  métrica OTel).
- **AR-60** (D-03a) backend-com: timeout de 2 s → 15–30 s, retry com backoff, e um marcador
  de pendência quando falhar.
- **AR-61** Conferir se o `reconcile_storage` encontra arquivo sem `Document` e o importa.
  Se não, implementar. Agendar via CronJob.
- **AR-62** (D-03b, depois) O com envia os bytes ao core, e o core grava no storage e cria
  o documento numa transação.
- **AR-63** Remover o `_auth` morto do backend-com (A5).
- **AR-64** Autenticação por token interno nas rotas do backend-ocr (A3), mais NetworkPolicy
  (AR-74).
- **AR-65** (D-07) Definir o dono da classificação. Restringir o classifier do backend-ocr
  à escolha de motor.

## Fase 4 — Operação

- **AR-70** CronJobs: `sweep_stuck_documents`, polls do backend-com (descobrir quem chama
  `/poll` hoje: B3), `reconcile_storage`.
- **AR-71** Métricas: pipeline de métricas no otel-collector e métricas de negócio
  (documentos por estado, idade do mais antigo em processamento, erros por etapa, 429s).
- **AR-72** `/ready` real: o core checa o banco, e o backend-ocr checa se há pelo menos 1
  motor carregado.
- **AR-73** Alertas: fila parada há mais de 15 min, documentos presos, taxa de erro de
  OCR, CrashLoop.
- **AR-74** NetworkPolicy: só o core acessa o backend-ocr, e só o ingress acessa core e com.
- **AR-75** Backups: `pg_dump` em CronJob, com retenção e teste de restore. Versionamento e
  lifecycle no bucket.
- **AR-76** Dockerfiles de backend com `USER` não-root.
- **AR-77** Frontend Dockerfile: Node 20, `.env` no `.dockerignore`, e deixar claro que é só
  para dev (deploy em Cloudflare Pages).

## Fase 5 — Qualidade contínua

- **AR-80** Front: interceptor de 401 com `/api/auth/refresh` e fila de requisições durante
  o refresh (F1).
- **AR-81** Front: lazy routes por módulo com Suspense e error boundary por módulo (F2).
- **AR-82** Front: remover zustand, clsx, tailwind-merge e react-query-devtools, se
  continuarem sem uso (F4). Alinhar `max-lines` a 150 (F5).
- **AR-83** Front: tirar o estado de servidor do `AppLayout` e passá-lo para o TanStack
  Query (F3).
- **AR-84** Core: dividir `documents/views.py` (988 linhas) por subdomínio, sem mudar as
  URLs (B6).
- **AR-85** Core: renomear `backend-core/models/` (não é app) para `doc_schemas/` ou similar
  (B5). Mudança grande de imports: fazer isolada.
- **AR-86** OpenAPI com drf-spectacular e tipos gerados no front (F6).
- **AR-87** Testes do front em admin, upload e tenant-activation (F7).
