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

## Fase 2 — Processamento durável (depende de D-01)

> Detalhar só depois da decisão D-01. Esqueleto para a opção A (fila em Postgres):

- **AR-30** Modelo e lib da fila (por tenant: o job guarda `tenant_schema`). Migration nova
  ⚠️ (nova, não alteração de existente). Avaliar reaproveitar `orchestrator.OrchestrationRun`.
- **AR-31** `enqueue` transacional no ponto onde hoje há `submit_document_processing`
  (`documents/views.py:305`, `processing_queue.py`).
- **AR-32** Comando `run_worker` (SKIP LOCKED, troca de schema, heartbeat, encerramento
  gracioso no SIGTERM).
- **AR-33** Idempotência por `(document_id, step)`: o OCR reaproveita o texto salvo, e a
  transição de estado usa `select_for_update` (P4). Duplicado por sha256, não por nome.
- **AR-34** Recuperação: o job com heartbeat vencido volta para a fila. Remover o pool em
  memória.
- **AR-35** Deployment `docuparser-core-worker` (mesma imagem, outro comando) em compose e
  k8s.
- **AR-36** Testes: restart no meio do processamento, envio duplo, erro permanente versus
  transitório.
- **AR-40** Redis: remover do compose e do k8s (se D-01 = A e D-04 = a), junto com o
  `docuparse_events`.

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
