# Achados da revisão de arquitetura (2026-11-26)

Severidade: **S1** é risco de produção, segurança ou perda de dados. **S2** é confiabilidade,
custo ou manutenção relevante. **S3** é limpeza ou débito menor.
Os caminhos são relativos a `docuparse-project/`, salvo indicação. As linhas são as de
2026-11-26 (commit `36e5fd96`); confira antes de editar.

Legenda de verificação: ✅ conferido à mão nesta revisão · 🔎 relatado por scout, não conferido.

---

## 1. Visão geral do que existe hoje

```
                 ┌──────────── frontend (React 19 / Vite / TanStack Query) ───────────┐
                 │                         Cloudflare Pages                           │
                 └───────────────┬───────────────────────────────┬────────────────────┘
                                 │ REST + JWT                    │ upload manual
                                 ▼                               ▼
 IMAP / Twilio ──► backend-com (FastAPI, ~1.4k LOC) ──HTTP 2s──► backend-core (Django, ~16k LOC prod)
                    │  grava arquivo no storage                   │  schema-por-tenant (django-tenants)
                    └─ XADD document.received ──► Redis (ninguém lê)
                                                                  │ ThreadPoolExecutor(2) em memória
                                                                  ├─HTTP 300s─► backend-ocr (FastAPI, ~7.5k LOC)
                                                                  ├─HTTP 120s─► langextract (FastAPI, 574 LOC)
                                                                  ├──────────► Superlógica (ERP, travado)
                                                                  └─ Postgres · MinIO/S3 · OTel→Jaeger
```

Pacotes compartilhados, copiados em cada imagem via `PYTHONPATH` (sem versão):
`shared/docuparse_storage` (540 LOC), `docuparse_orchestrator` (284), `docuparse_observability`
(205), `docuparse_events` (189), `contracts/events/schemas.py` (287).

---

## 2. Processamento de documentos (backend-core)

| # | Sev | Achado | Evidência |
|---|---|---|---|
| P1 | S1 | **Trabalho só em memória.** O `ThreadPoolExecutor(max_workers=2)` tem fila sem limite. Num restart ou deploy, o que está na fila ou em execução se perde, e o `OrchestrationRun` fica RUNNING. | ✅ `backend-core/documents/services/processing_queue.py:14-15` |
| P2 | S1 | **O sweeper não cobre tudo e ninguém o agenda.** `sweep_stuck_processing` só recupera documentos em RECEIVED. Um documento em OCR_COMPLETED com `metadata.extraction.state="running"` nunca é varrido. O comando `sweep_stuck_documents` não está em cron, compose nem k8s. | 🔎 `documents/services/processing_recovery.py:58-100` |
| P3 | S2 | **Os retries cobram de novo.** O decorator `task()` repete a função inteira 3x com tenacity, sem distinguir os tipos de erro. Cada tentativa de `ocr_task` chama o OCR pago (OpenRouter) outra vez, inclusive em erros não transitórios (4xx, JSON inválido). | ✅ `shared/docuparse_orchestrator/decorators.py:24,53`; `ocr_processor.py:170,319` |
| P4 | S2 | **Não há proteção contra processamento duplo.** Nenhum `select_for_update` ou lock de estado guarda o início do OCR ou da extração. O duplicado é detectado por `original_filename`, não por sha256. | 🔎 `documents/services/event_consumers.py:65` |
| P5 | S2 | **Não há coordenação entre réplicas.** Cada pod tem seu pool. Hoje há uma réplica, então o problema não aparece. Escalar quebra a hipótese implícita. | 🔎 |
| P6 | S2 | **Threads sem `_with_fresh_connection`.** `_run_erp_dispatch` e `_run_langextract_safely` não fecham nem renovam a conexão, ao contrário da regra criada no incidente de 24/11. | 🔎 `processing_queue.py:~180` |
| P7 | S3 | Código morto e perigoso: `start_document_ocr_thread` cria uma thread daemon sem tenant e não tem chamadores. | 🔎 `ocr_processor.py:447-457` |
| P8 | S2 | Não há rate limit, backoff para 429 nem circuit breaker para o OpenRouter (OCR e extração). O único retry é o fallback de modelo para texto vazio. | 🔎 `backend-ocr/.../openrouter_engine.py:350-404` |

**Diagnóstico:** essa é a principal fraqueza arquitetural. Falta uma **fila de jobs durável**
com estado persistido, retry classificado e idempotência por documento e etapa. Ver
[target-architecture.md §3](target-architecture.md).

---

## 3. Segurança e autenticação entre serviços

| # | Sev | Achado | Evidência |
|---|---|---|---|
| A1 | S1 | **`POST /api/ocr/process` é aberto.** É uma view Django pura, fora do DRF, com `@csrf_exempt` e sem autenticação. Recebe um arquivo e dispara OCR (custo de OpenRouter). | ✅ `backend-core/documents/views.py:183-190`, `documents/urls.py:50` |
| A2 | S1 | **O token interno fica aberto quando não está configurado** (`_internal_token_error` retorna `None`). A mensagem do 401 contém a string de teste `"teste456"`. | ✅ `documents/views.py:146-156` |
| A3 | S2 | backend-ocr e langextract **não têm autenticação** e dependem só do isolamento de rede. Não existe NetworkPolicy no k8s. | 🔎 `backend-ocr/api/app.py`, `langextract-service/api/app.py` |
| A4 | S2 | O middleware de tenant lê o claim `tenant` do JWT **sem verificar a assinatura**. A autenticação acontece depois, o que limita o risco, mas é um cheiro na fronteira de confiança. | ✅ `tenants/middleware.py:105-106` |
| A5 | S2 | O backend-com tem um `_auth` que não está ligado a nenhuma rota e aceita qualquer string com 3 segmentos. Se alguém o ligar, vira um furo. | 🔎 `backend-com/api/app.py:119-134` |
| A6 | S1 | **Repositório k8s** (repo separado): `apps/voicekeeper/.env` e `secrets/k3s-token-novo.txt` estão versionados em texto puro. Não é do DocuParser, mas está no mesmo repo de deploy. | ✅ `git ls-files` em `innovox-kubernetes-deployments` |

---

## 4. Implantação e operação

| # | Sev | Achado | Evidência |
|---|---|---|---|
| D1 | S1 | **O backend-core roda `runserver` em prod**: o Dockerfile e o `entrypoint.sh` usam o servidor de desenvolvimento do Django. O CMD do Dockerfile roda `migrate` (só public), e não `migrate_schemas`. | ✅ `backend-core/Dockerfile` (CMD), `backend-core/entrypoint.sh:20` |
| D2 | S1 | **`DEBUG: "True"` no ConfigMap de prod.** | ✅ `innovox-kubernetes-deployments/apps/docuparser/prod/config-map.yaml:7` |
| D3 | S1 | **As probes estão comentadas** nos 4 deployments de prod (e de hml). Não há resource requests nem limits, PDB, HPA ou NetworkPolicy. | ✅ `prod/docuparser-*/deployment.yaml:30,37` |
| D4 | S1 | **O CI não roda testes de backend.** `ci.yaml` só compila e publica imagens. Não roda pytest, ruff nem `makemigrations --check`. Só o frontend tem lint, typecheck e testes. | ✅ `.github/workflows/ci.yaml`; 🔎 `frontend-ci.yaml:38-45` |
| D5 | S2 | Tags de imagem mutáveis: a mesma tag `0.0.14` foi publicada 3 vezes. A versão é única para os 4 serviços e o bump é manual no `pyproject.toml` da raiz. O k8s está em `0.0.14` e o repo, em `0.0.15`. | 🔎 |
| D6 | S2 | O frontend usa `node:18-alpine` (as dependências exigem Node ≥20), roda `npm run dev` como CMD e o `.dockerignore` não exclui `.env`. O deploy real é Cloudflare Pages, então o Dockerfile serve só para dev. Deixar isso claro ou corrigir. | 🔎 `frontend/Dockerfile:1,9` |
| D7 | S2 | As imagens de backend não têm `USER` (rodam como root) nem `HEALTHCHECK`. | 🔎 |
| D8 | S2 | Observabilidade só de traces: o otel-collector não tem pipeline de métricas nem de logs, e não há alertas. O incidente de 24/11 (processamento parado sem erro) não teria alertado ninguém. | 🔎 `otel-collector-config.yaml:85-90` |
| D9 | S2 | O `/ready` do core não checa o banco nem as dependências. O do backend-ocr checa só env vars. | 🔎 `backend-core/documents/views.py:83-86`, `backend-ocr/api/app.py:109-131` |
| D10 | S3 | A config está espalhada por `.env`, compose, ConfigMap e defaults de Dockerfile, sem uma tabela única das env vars. | 🔎 |
| D11 | S2 | Os únicos backups são de dados locais (`scripts/backup_local_data.sh`). Não há rotina de backup do Postgres nem do S3 em hml ou prod. | 🔎 |

---

## 5. Fronteiras de serviço

| # | Sev | Achado | Evidência |
|---|---|---|---|
| B1 | S2 | **O langextract é um serviço fino demais.** São 574 LOC: uma chamada `urllib` ao OpenRouter com recuperação de JSON, sem retry, com um único chamador (o core). Duplica o cliente OpenRouter do backend-ocr, que já tem lógica de LLM (`field_extractor_impl.py`). Custa um container, um deploy, um health check e uma env de modelo a mais. | 🔎 `langextract-service/domain/llm_extractor.py:~230` |
| B2 | S1 | **A entrega do backend-com para o core é frágil.** O backend-com grava o arquivo, publica no Redis (sem leitor) e faz um POST no core com timeout de 2 s, sem retry. Se o POST falhar, só registra um warning: o arquivo fica no storage sem linha no banco e o documento some do ponto de vista do usuário. | 🔎 `backend-com/services/document_ingest.py:87,117-150` |
| B3 | S3 | O backend-com não tem loop próprio: os polls de IMAP e Twilio dependem de alguém chamar `/poll`. Confirmar quem chama em hml/prod (o cron não foi encontrado no repo k8s). | 🔎 |
| B4 | S2 | **Há três classificadores:** `backend-ocr/domain/classifier.py` (503 LOC, tipo de arquivo e imagem), `backend-core/models/classifier.py` (scoring de texto → `schema_id`) e `backend-core/accounting/classification/` (regras de conta contábil). O primeiro e o terceiro têm papéis distintos. O segundo pode competir com o catálogo e o LLM. Definir um único dono para "qual é o tipo do documento". | 🔎 |
| B5 | S3 | `backend-core/models/` não é um app Django (0 models). Guarda definições de schema (boleto 857 linhas, nota fiscal 619...) e o classifier. O nome confunde com `models.py`. | 🔎 |
| B6 | S3 | `documents` é o app mais pesado (6.3k LOC): `views.py` tem 988 linhas e mistura ingestão, processamento, dashboard, pagamentos e ERP. Separar views e serviços por subdomínio (por exemplo `documents/payments`, `documents/processing`) sem criar um serviço novo. | 🔎 |

---

## 6. Sobras da arquitetura antiga (eventos, Camunda, DLQ, layout)

| # | Sev | Sobra | Evidência |
|---|---|---|---|
| L1 | S2 | `DOCUPARSE_EVENT_BUS=redis` e `REDIS_URL` em core, com, ocr e langextract (compose e ConfigMap de prod). Redis é `depends_on` obrigatório dos 4. O `xadd` não tem MAXLEN, então as streams **crescem sem limite** no Redis. | 🔎 `docker-compose.yml:20,177,229,278,323`; `shared/docuparse_events/__init__.py:95`; ✅ `prod/config-map.yaml:9` |
| L2 | S3 | `consume`/`consume_entries` em `docuparse_events` não têm chamador em prod. Também sem uso: `shared/consume_fake_event.py` e `publish_fake_event.py`. | 🔎 |
| L3 | S3 | Classes de contrato mortas: `OCRCompletedEvent`, `OCRFailedEvent`, `LayoutClassifiedEvent`, `ExtractionCompletedEvent`. | 🔎 `contracts/events/schemas.py` |
| L4 | S3 | A dependência `redis` e o `RedisInstrumentor` continuam no backend-ocr e no langextract, que não usam Redis. Os `pyproject.toml` dos dois ainda se chamam `atoms`, com a descrição "Backend Core". | 🔎 |
| L5 | S3 | O ConfigMap de prod mantém as flags `*_WORKER_ENABLED=false` (linhas 14-18), com um comentário mandando removê-las quando a imagem sem workers subir. | 🔎 |
| L6 | S3 | Diretórios vazios não versionados: `camunda-workers/` e `layout-service/` (só `__pycache__`), e `backend-core/not-used-with-s3/` (134 arquivos não versionados). | ✅ |
| L7 | S3 | Volume `docuparse-events` no compose (core, com e langextract). | 🔎 `docker-compose.yml:149,218,314,367` |
| L8 | S3 | O `pyproject.toml` da raiz lista docling, fitz e pytesseract, que nenhum serviço usa por ali. | 🔎 |
| L9 | S3 | O `ci.yaml:18` referencia `steps.check_version.outputs.SKIP`, que não existe. | 🔎 |
| L10 | S3 | Texto desatualizado sobre Zeebe em `shared/docuparse_observability/tracing.py:135`, e um comentário de DLQ em `frontend/vitest.config.ts:32`. | 🔎 |
| L11 | S3 | `print()` em `backend-core/documents/services/ocr_client.py`. | 🔎 |

**Não é sobra:** a permissão `operations.access` **continua de propósito**. Ela libera o
dashboard de processos e o retry de etapa (decisão da remoção de 2026-11-26). Só o nome
ficou estranho. Uma eventual renomeação (por exemplo `processes.access`) é opcional e exige
migração de dados das roles.

**Não é bug:** com `SuperlogicaMode.DISABLED`, o documento fica em
ERP_INTEGRATION_REQUESTED. **É intencional.** Não "consertar".

---

## 7. Frontend

O frontend está saudável: TypeScript strict, sem `.js`, `tsc` limpo e 202 testes.

| # | Sev | Achado | Evidência |
|---|---|---|---|
| F1 | S2 | **Sem refresh de token.** O `refresh_token` é salvo mas nunca usado, e não há interceptor de resposta para 401. O backend já tem `/api/auth/refresh`. | 🔎 `shared/lib/http.ts:17-23`, `modules/auth/context.tsx:43` |
| F2 | S3 | Nenhuma rota usa lazy loading (o `frontend_rules.md` pede): o `router.tsx` importa todos os módulos de forma eager. | 🔎 `app/router.tsx:1-10` |
| F3 | S3 | O `AppLayout` busca dados com `useEffect` e guarda estado de servidor (`refreshSignal`, `selectedDocument`). | 🔎 `app/AppLayout.tsx:62-66` |
| F4 | S3 | Dependências sem uso: zustand, clsx, tailwind-merge, @tanstack/react-query-devtools. | 🔎 |
| F5 | S3 | O ESLint usa `max-lines` 200, e as regras pedem 150. | 🔎 |
| F6 | S3 | Os tipos de API são escritos à mão. O DRF poderia expor OpenAPI (drf-spectacular) e gerar os tipos. Isso é opcional, mas evita deriva entre front e back. | 🔎 |
| F7 | S3 | admin, upload, tenant-activation e shared/components não têm testes. O `TYPESCRIPT_MIGRATION.md:421` ainda lista o item de Operações/DLQ. | 🔎 |

---

## 8. Documentação

| # | Sev | Achado |
|---|---|---|
| X1 | S2 | `docs/architecture.md` (raiz) descreve 3 serviços com portas erradas e não menciona backend-com, langextract, storage nem o fluxo atual. É o primeiro lugar onde alguém procura. |
| X2 | S3 | Docs desatualizados em relação ao que foi removido: `docuparse-project/README.md:59,77-78,89-90`, `docuparse-project/docs/TECHNICAL.md:34,256,819`, `.env.example:73-76`, `docs/langextract_integration_map.md`, `docs/fixplans/*`, `docs/specs/020-*/contracts/event-schema-trace-context.md`. |
| X3 | S3 | Os READMEs do langextract e do backend-ocr estão vazios ou genéricos. |
| X4 | S3 | `/docuparser/scripts/docker-compose.yml` é um experimento OLMOCR que não tem relação com o produto. |
