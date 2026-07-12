# resources.md — Recursos necessários para o DocuParse

Referência única dos recursos de infraestrutura e serviços externos que o projeto
precisa para rodar (dev e produção): banco de dados, storage (S3/MinIO), Redis,
banco vetorial, serviços externos (LLM, WhatsApp, e-mail) e a orquestração
opcional (Camunda 8).

> Fonte da verdade da configuração: [`docuparse-project/docker-compose.yml`](docuparse-project/docker-compose.yml),
> [`docuparse-project/backend-core/core/settings.py`](docuparse-project/backend-core/core/settings.py)
> e [`docuparse-project/.env.example`](docuparse-project/.env.example). Ao mudar
> qualquer recurso, **atualize este arquivo e o `.env.example`** (ver guia de PR).

---

## 1. Visão geral (topologia)

| Recurso | Serviço (compose) | Porta host → container | Volume (persistência) | Obrigatório? |
|---|---|---|---|---|
| **Banco de dados** (PostgreSQL 16) | `postgres` | `5432 → 5432` | `postgres-data` | ✅ Sim |
| **Storage de objetos** (MinIO/S3) | `minio` + `minio-setup` | `${MINIO_API_PORT:-9002} → 9000` (API S3) · `${MINIO_CONSOLE_PORT:-9003} → 9001` (console) | `minio-data` | ✅ Sim (backend `s3`) |
| **Cache / Event bus** (Redis 7) | `redis` | `6380 → 6379` | `redis-data` | ✅ Sim |
| **Frontend** (React/Vite) | `frontend` | `5173 → 5173` | — | ✅ Sim |
| **API principal** (Django/DRF) | `backend-core` | `8000 → 8000` | `docuparse-storage`, `docuparse-events` | ✅ Sim |
| **Ingestão** (FastAPI) | `backend-com` | `8070 → 8070` | idem | ✅ Sim |
| **OCR** | `backend-ocr` | `8080 → 8080` | idem | ✅ Sim |
| **Layout** | `layout-service` | `8090 → 8090` | idem | ✅ Sim |
| **Extração** (LangExtract) | `langextract-service` | `8091 → 8091` | idem | ✅ Sim |
| Workers assíncronos | `backend-core-events`, `backend-ocr-worker`, `layout-worker`, `langextract-worker` | — (sem porta) | idem | ⚙️ Profile `async-workers` |
| Orquestração BPMN (Camunda 8) | `zeebe`, `operate`, `tasklist`, `elasticsearch`, `camunda-workers` | ver §7 | `zeebe-data`, `elasticsearch-data` | ⚙️ Profile `camunda` |

> **Banco vetorial (Qdrant/Milvus): NÃO é usado neste projeto.** Não há Qdrant,
> Milvus, pgvector ou similar no código nem no compose. (Um container
> `milvus-minio` pode aparecer no host de dev por causa de **outro** projeto — não
> faz parte do DocuParse; é só a origem do conflito de porta 9000, ver o README da
> feature 011.)

### Perfis do Compose
- **Base (sem profile):** postgres, redis, minio(+setup), frontend e os 5 serviços de I/O. `docker compose up` sobe só isso.
- **`async-workers`:** workers de OCR/layout/extração/eventos desacoplados. `docker compose --profile async-workers up`.
- **`camunda`:** orquestração BPMN (Zeebe/Operate/Tasklist/Elasticsearch). `docker compose --profile camunda up`.

---

## 2. Banco de dados — PostgreSQL

- **Engine:** `django.db.backends.postgresql`.
- **Nome do banco usado no código:** **`docuparse`** (`POSTGRES_DB`, default `docuparse`).
- **Seleção de banco (ordem de prioridade em `settings.py`):**
  1. `DATABASE_URL` (se definido) → parse da URL; nome default `docuparse`.
  2. `POSTGRES_HOST` → usa `POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_HOST`/`POSTGRES_PORT`.
  3. **Fallback SQLite** (`BASE_DIR/db.sqlite3`, dentro do container) — só para dev/teste sem Postgres. Defina `DOCUPARSE_REQUIRE_POSTGRES=1` para **proibir** o fallback em produção.
- **Variáveis:** `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` (ou `DATABASE_URL`).
- **Defaults dev (compose):** db/user/password = `docuparse` / `docuparse` / `docuparse`, host `postgres`, porta `5432`.
- **Persistência:** volume `postgres-data`.
- **Migrations:** o `backend-core` roda `python manage.py migrate --noinput` no start.

**Como validar:**
```bash
docker compose exec postgres psql -U docuparse -d docuparse -c "select 1;"
docker compose exec postgres psql -U docuparse -d docuparse -c "\dt documents_*"
```

---

## 3. Storage de objetos — MinIO / S3 (feature 011)

Armazena os **binários dos documentos** e o **texto bruto (`raw_text.json`)**. Os
metadados e relacionamentos ficam no Postgres, referenciando o objeto por URI
(`s3://<bucket>/<key>`). Ver [docs da feature 011](docs/specs/011-shared-object-storage/README.md).

- **Bucket usado no código:** **`docuparse`** (`S3_BUCKET`). Criado em dev pelo serviço `minio-setup`; em **produção é provisionado pela infra** (a aplicação não cria bucket em runtime, por design).
- **Endpoint interno:** `http://minio:9000` (`S3_ENDPOINT_URL`). Vazio ⇒ AWS S3 nativo.
- **Convenção de keys:** `documents/{tenant_id}/{document_id}/original` · `documents/{tenant_id}/{document_id}/ocr/raw_text.json`.
- **Seleção de backend:** `DOCUPARSE_STORAGE_BACKEND` = `s3` (compartilhado) ou `local` (disco/volume, comportamento antigo).
- **Variáveis:** `DOCUPARSE_STORAGE_BACKEND`, `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (+ dev: `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_API_PORT`, `MINIO_CONSOLE_PORT`).
- **Credenciais:** `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` derivam de `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`. **Sem default no compose** — devem vir do `.env` (dev) ou de **Secret** (produção). Nunca versionar credenciais reais.
- **Portas do host (só dev):** configuráveis via `MINIO_API_PORT`/`MINIO_CONSOLE_PORT` (default `9002`/`9003`; remapeáveis se ocupadas). Não afetam a comunicação interna (`minio:9000`).
- **Persistência:** volume `minio-data`.

**Como validar:**
```bash
docker compose exec minio-setup mc ls local/docuparse            # bucket existe
# console web: http://localhost:${MINIO_CONSOLE_PORT:-9003}  (login = MINIO_ROOT_USER/PASSWORD)
docker compose exec postgres psql -U docuparse -d docuparse \
  -c "select file_uri, raw_text_uri from documents_document limit 3;"  # URIs devem ser s3://docuparse/...
```

**Utilitários de manutenção** (dentro de `backend-core`):
```bash
python manage.py migrate_storage_local_to_s3 --dry-run|--apply   # migra local:// → s3://
python manage.py reconcile_storage [--direction storage-to-db --delete-orphans]  # reconcilia banco ↔ MinIO
```

---

## 4. Cache / Event bus — Redis

- **Uso:** barramento de eventos (Redis Streams) entre os serviços; seleção via `DOCUPARSE_EVENT_BUS=redis`.
- **URL interna:** `redis://redis:6379/0` (`REDIS_URL`).
- **Porta host:** `6380 → 6379`.
- **Variáveis:** `DOCUPARSE_EVENT_BUS` (`redis`), `REDIS_URL`. Modo local alternativo: `DOCUPARSE_EVENT_BUS` não-redis + `DOCUPARSE_LOCAL_EVENT_DIR` (arquivo, só dev/testes).
- **Persistência:** volume `redis-data` (AOF).

**Como validar:**
```bash
docker compose exec redis redis-cli ping        # PONG
docker compose exec redis redis-cli xinfo stream <stream>   # se quiser inspecionar o event bus
```

---

## 5. Banco vetorial — Qdrant / Milvus

**Não aplicável.** O DocuParse não utiliza banco vetorial. Caso venha a ser
adicionado no futuro (ex.: busca semântica), documentar aqui: serviço, porta,
coleção usada no código, credenciais e volume, e atualizar o `.env.example`.

---

## 6. Serviços externos (SaaS / APIs)

| Serviço | Papel | Variáveis | Obrigatório? |
|---|---|---|---|
| **OpenRouter** | LLM para OCR/classificação/extração | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, `OPENROUTER_FALLBACK_MODEL`, `LANGEXTRACT_MODEL` | ✅ (motor LLM principal) |
| **OpenAI** | LLM alternativo | `OPENAI_API_KEY` | ⚙️ Opcional |
| **Twilio** | Ingestão via WhatsApp | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_API_KEY_SID`, `TWILIO_API_KEY_SECRET`, `TWILIO_FROM_NUMBER`, `NUMERO_WHATSAPP_TESTE` | ⚙️ Só se usar canal WhatsApp |
| **Servidor IMAP** | Ingestão via e-mail | `imap_reader_host`, `imap_reader_username`, `imap_reader_password`, `imap_reader_port`, `imap_reader_ssl`, `imap_reader_folder`, `DOCUPARSE_IMAP_PASSWORD`, `imap_reader_webhook_url` | ⚙️ Só se usar canal e-mail |

Outras configs de aplicação relevantes: `OCR_LANGUAGE`, flags `DOCUPARSE_*_WORKER_ENABLED`,
`DOCUPARSE_AUTO_PROCESS_OCR`, conta admin (`DOCUPARSE_ADMIN_EMAIL/USERNAME/PASSWORD`),
token interno de serviço (`DOCUPARSE_INTERNAL_SERVICE_TOKEN`).

**Como validar:** health dos serviços que consomem essas APIs:
```bash
curl -fsS http://localhost:8000/api/ocr/health   # backend-core
curl -fsS http://localhost:8070/health           # backend-com (ingestão)
curl -fsS http://localhost:8080/health           # backend-ocr
curl -fsS http://localhost:8090/health           # layout
curl -fsS http://localhost:8091/health           # langextract
```

---

## 7. Orquestração BPMN — Camunda 8 (profile `camunda`, opcional)

Usado apenas quando a orquestração via workflow está habilitada.

| Serviço | Papel | Porta host → container | Volume |
|---|---|---|---|
| `zeebe` | Workflow engine (gRPC) | `26500 → 26500`, `8088 → 8080` | `zeebe-data` |
| `operate` | UI de operação | `8081 → 8080` | — |
| `tasklist` | UI de tarefas | `8082 → 8080` | — |
| `elasticsearch` | Índice do Operate/Tasklist | `9200 → 9200` | `elasticsearch-data` |
| `camunda-workers` | Job workers (chamam os backends) | — | monta `./bpmn` |

- **Variáveis:** `ZEEBE_ADDRESS` (`zeebe:26500`), `DOCUPARSE_INTERNAL_SERVICE_TOKEN`.
- **Subir:** `docker compose --profile camunda up`.

---

## 8. Variáveis de ambiente

- **Template:** [`docuparse-project/.env.example`](docuparse-project/.env.example). Fluxo: `cp .env.example .env` e ajuste.
- O `.env` real é **gitignored** e nunca versionado. Em produção, segredos vêm de **Secret** (k8s/Vault), não do `.env` nem de defaults do compose.
- **Regra:** toda alteração que envolva variável de ambiente/infra deve atualizar `.env.example` **e** este `resources.md` (ver guia de PR).

---

## 9. Volumes (dados persistentes)

`postgres-data`, `redis-data`, `minio-data`, `docuparse-storage` (modo `local`),
`docuparse-events` (event bus local), `elasticsearch-data`, `zeebe-data`.

> Em produção, esses dados normalmente moram em serviços gerenciados (RDS, S3,
> ElastiCache, etc.), não em volumes Docker locais.

---

## 10. Checklist de deploy / validação

1. **Provisionar recursos gerenciados** (prod): Postgres (`docuparse`), bucket S3 (`docuparse`), Redis; e Camunda/Elasticsearch se o profile estiver em uso.
2. **Segredos via Secret** (nunca no código): credenciais Postgres, `AWS_*`/S3, `OPENROUTER_API_KEY`/`OPENAI_API_KEY`, `TWILIO_*`, IMAP, `DOCUPARSE_INTERNAL_SERVICE_TOKEN`, conta admin.
3. **Migrations aplicadas** (`manage.py migrate`).
4. **Storage:** bucket existe e `DOCUPARSE_STORAGE_BACKEND=s3`; URIs novas gravam como `s3://docuparse/...` (validar com o `psql` da §3).
5. **Healthchecks** dos 5 serviços de I/O (§6) retornando 200; Postgres/Redis/MinIO *healthy*.
6. **Event bus:** `DOCUPARSE_EVENT_BUS=redis` e `redis-cli ping` = PONG.
7. Se o deploy falhar: **nova branch + novo PR** com a correção; em rollback, voltar à versão anterior de forma controlada (ver guia de PR).
