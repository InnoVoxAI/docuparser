# Documentação Técnica — DocuParse

## Índice

1. [Visão Geral da Arquitetura](#visão-geral-da-arquitetura)
2. [Como Executar Localmente](#como-executar-localmente)
3. [Estrutura do Projeto](#estrutura-do-projeto)
4. [Front-end](#front-end)
5. [Back-end Core](#back-end-core-backend-core)
6. [Serviço de Captura de Documentos](#serviço-de-captura-backend-com)
7. [Serviço de OCR](#serviço-de-ocr-backend-ocr)
8. [Serviço de Extração de Campos](#serviço-de-extração-langextract-service)
9. [Banco de Dados](#banco-de-dados)
10. [Estrutura do Banco de Dados](#estrutura-do-banco-de-dados)
11. [Eventos e Mensageria](#eventos-e-mensageria)
12. [Observabilidade e Rastreamento Distribuído](#observabilidade-e-rastreamento-distribuído)
13. [Autenticação e Permissões](#autenticação-e-permissões)
14. [Variáveis de Ambiente](#variáveis-de-ambiente)

---

## Visão Geral da Arquitetura

O DocuParse é um sistema de processamento de documentos baseado em microsserviços. Cada serviço tem uma responsabilidade bem definida; o processamento de documentos usa chamadas HTTP do backend-core para o OCR e a extração.

| Componente | Tecnologia | Porta | Responsabilidade |
|---|---|---|---|
| Front-end | React + Vite | 5173 | Interface do usuário |
| backend-core | Django + DRF | 8000 | Orquestração, API principal, autenticação |
| backend-com | FastAPI | 8070 | Captura de documentos (upload, email, WhatsApp) |
| backend-ocr | FastAPI | 8080 | Processamento OCR (extração de texto) |
| langextract-service | FastAPI | 8091 | Extração de campos com LLM |
| PostgreSQL | postgres:16 | 5432 | Banco de dados relacional |
| Redis | redis:7 | 6380 | Barramento de eventos + cache |
| MinIO | minio | 9000/9001 | Object storage (arquivos e textos) |
| OTel Collector | otel-collector-contrib | 4317 (gRPC) / 4318 (HTTP) | Coleta OTLP, redação básica, tail sampling |
| Jaeger | jaeger all-in-one | 16686 (UI) | Armazenamento e visualização de traces |

### Fluxo Principal

```
[Usuário / E-mail / WhatsApp]
         |
         v
   backend-com (captura)
         | HTTP POST: document.received
         v
   backend-core (registra documento)
         | thread interna
         v
   backend-ocr (OCR — extração de texto)
         | auto_extract_after_ocr()
         v
   langextract-service (extração de campos com LLM)
         |
         v
   ExtractionResult salvo → status VALIDATION_PENDING
         |
         v
   [Operador valida / aprova / rejeita no front-end]
```

---

## Como Executar Localmente

### Pré-requisitos

- Docker e Docker Compose instalados
- Arquivo `.env` configurado na raiz de `docuparse-project/` (ver seção [Variáveis de Ambiente](#variáveis-de-ambiente))

### Subir todos os serviços

```bash
cd docuparse-project/
docker compose up --build
```

A imagem do `backend-core` tem dois modos (`backend-core/entrypoint.sh`):

- **`release`**: `migrate_schemas --shared`, `migrate_schemas` (tenants) e `seed_data`,
  e sai. Roda uma vez por deploy. No compose, é o serviço `backend-core-release`, e o
  `backend-core` só sobe depois que ele termina com sucesso.
- **`web`** (padrão): `gunicorn core.wsgi` com **1 worker** e threads. Um worker só,
  de propósito: o processamento roda num `ThreadPoolExecutor` em memória, e cada worker
  criaria o próprio pool. Isso vale até existir a fila durável.

| Variável | Padrão | Descrição |
|---|---|---|
| `DOCUPARSE_MIGRATE_ON_BOOT` | `true` | Se `true`, o modo `web` roda o `release` antes de subir (compatível com o CMD antigo). O compose usa `false`. No k8s, passar para `false` quando o release virar initContainer ou Job |
| `GUNICORN_THREADS` | `4` | Threads do worker do gunicorn |
| `GUNICORN_TIMEOUT` | `120` | Timeout de requisição do gunicorn, em segundos |
| `GUNICORN_CMD_ARGS` | — | Flags extras lidas pelo próprio gunicorn. O compose usa `--reload` |

O `/admin/` do Django perde o CSS sem o `runserver`: não há `STATIC_ROOT` nem whitenoise.

### Conta admin padrão

| Campo | Valor padrão |
|---|---|
| E-mail | `admin@docuparse.com` |
| Senha | `admin123` |

Para sobrescrever na produção, defina no `.env`:
```
DOCUPARSE_ADMIN_EMAIL=seu@email.com
DOCUPARSE_ADMIN_PASSWORD=suasenha
```

### Acesso à interface

Após o startup: `http://localhost:5173`

### Comandos úteis

```bash
# Ver logs de um serviço específico
docker compose logs -f backend-core

# Executar comando Django dentro do container
docker compose exec backend-core python manage.py shell

# Acessar o banco de dados diretamente
docker compose exec postgres psql -U docuparse -d docuparse
```

---

## Estrutura do Projeto

```
docuparse-project/
├── frontend/                  # React SPA (Vite)
│   └── src/
│       ├── main.jsx           # Aplicação completa (SPA)
│       └── models/            # Schemas de extração por tipo de documento
│           ├── boleto/
│           ├── contadeagua/
│           ├── nota_fiscal/
│           └── recibo/
│
├── backend-core/              # Django — API principal
│   ├── core/
│   │   ├── settings.py        # Configurações Django
│   │   └── urls.py            # Roteamento principal
│   ├── documents/             # App de documentos
│   │   ├── models.py          # Modelos do banco
│   │   ├── views.py           # Endpoints da API
│   │   ├── services/          # Lógica de negócio
│   │   │   ├── ocr_processor.py       # Processamento OCR + extração automática
│   │   │   ├── ocr_client.py          # Client HTTP para backend-ocr
│   │   │   └── langextract_client.py  # Client HTTP para langextract-service
│   │   └── management/commands/
│   │       └── sweep_stuck_documents.py
│   ├── users/                 # App de usuários
│   │   ├── models.py          # Permission, Role
│   │   ├── auth_views.py      # Login, logout, refresh
│   │   ├── user_views.py      # CRUD de usuários
│   │   └── management/commands/
│   │       ├── seed_permissions.py
│   │       └── seed_admin.py
│   └── models/                # Heurísticas de classificação de texto
│       ├── nota_fiscal/schemas.py
│       ├── boleto/schemas.py
│       └── contadeagua/schemas.py
│
├── backend-com/               # FastAPI — captura de documentos
│   └── src/backend_com/
│       ├── api/app.py         # Rotas FastAPI
│       ├── config.py          # Configurações
│       └── atoms/             # Módulos funcionais (email, whatsapp, upload)
│
├── backend-ocr/               # FastAPI — OCR
│   └── api/app.py             # Endpoint /api/v1/documents/process
│
├── langextract-service/       # FastAPI — extração LLM
│   └── api/app.py             # Endpoint /api/v1/extract
│
│   └── api/app.py             # Endpoint /api/v1/classify-layout
│
├── contracts/                 # Schemas de eventos compartilhados
│   └── events/schemas.py      # Pydantic: DocumentReceivedEvent, OCRCompletedEvent, etc.
│
├── shared/                    # Utilitários compartilhados
│   ├── docuparse_storage/     # Abstração de storage local
│   ├── docuparse_events/      # Abstração do barramento de eventos
│   └── docuparse_observability/ # Logging estruturado
│
├── docker-compose.yml         # Orquestração completa
├── .env                       # Variáveis de ambiente
└── scripts/
    └── backup_local_data.sh   # Backup dos volumes Docker
```

---

## Front-end

### Tecnologia

| Item | Valor |
|---|---|
| Framework | React 18.2.0 |
| Build tool | Vite 5.0.8 |
| Linguagem | JavaScript (JSX) |
| Estilos | Tailwind CSS 3.4.1 |

### Principais Bibliotecas

| Biblioteca | Finalidade |
|---|---|
| `axios` | Consumo de APIs HTTP |
| `lucide-react` | Ícones SVG |
| `tailwindcss` | Utilitários CSS |
| `tailwind-merge` | Merge de classes Tailwind |
| `clsx` | Composição de class names |

### Configuração (`vite.config.js`)

```js
// Proxy em desenvolvimento:
/api  →  http://127.0.0.1:8000   (backend-core)
/com  →  http://127.0.0.1:8070   (backend-com)
```

### Onde está configurada

- `frontend/package.json` — dependências
- `frontend/vite.config.js` — build e proxy
- `frontend/src/main.jsx` — aplicação completa (SPA de arquivo único)

### Modelos de Extração (frontend)

Os modelos definem os campos esperados por tipo de documento e são usados na tela de extração manual:

| Pasta | Tipo de documento |
|---|---|
| `src/models/boleto/` | Boleto bancário |
| `src/models/contadeagua/` | Conta de água |
| `src/models/nota_fiscal/` | Nota fiscal eletrônica |
| `src/models/recibo/` | Recibo de serviço |

### Navegação (NAV_ITEMS)

| ID | Label | Permissão necessária |
|---|---|---|
| upload | Upload | `documents.send` |
| inbox | Inbox | `inbox.view` |
| dashboard | Dashboard | `inbox.view` |
| validation | Validacao | `documents.validate` |
| settings | Configuracoes | `roles.manage` |
| users | Usuários | `users.manage` |
| roles | Roles | `roles.manage` |

---

## Back-end Core (`backend-core`)

### Tecnologia

| Item | Valor |
|---|---|
| Framework | Django 5.0.1 |
| API | Django REST Framework 3.14.0 |
| Autenticação | djangorestframework-simplejwt 5.3.1 |
| ORM | Django ORM |
| Banco | PostgreSQL (psycopg2-binary) |
| Cache/Eventos | Redis 7.4.0 |

### Arquitetura

O backend-core é organizado em dois apps Django:

- **`documents`** — documentos, configurações de schema/layout, extração, validação, ERP
- **`users`** — usuários, roles, permissões, autenticação JWT

### Endpoints da API

#### Documentos

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/ocr/documents` | Listar documentos |
| `GET` | `/api/ocr/documents/<uuid>` | Detalhe do documento |
| `DELETE` | `/api/ocr/documents/<uuid>/delete` | Excluir documento |
| `GET` | `/api/ocr/documents/<uuid>/file` | Download do arquivo original |
| `POST` | `/api/ocr/documents/<uuid>/process-ocr` | Disparar OCR manualmente |
| `POST` | `/api/ocr/documents/<uuid>/reprocess-ocr` | Reprocessar OCR |
| `POST` | `/api/ocr/documents/<uuid>/langextract` | Disparar extração manualmente |
| `POST` | `/api/ocr/documents/<uuid>/validate` | Validar / aprovar / rejeitar |
| `GET` | `/api/ocr/documents/<uuid>/erp` | Estado do lançamento da despesa no ERP, resumo do que será enviado e pendências |
| `POST` | `/api/ocr/documents/<uuid>/erp/confirm` | O analista confirma o envio ao ERP (permissão `erp.send`) |
| `POST` | `/api/ocr/documents/<uuid>/erp/retry` | Reenvio de uma falha retentável, com espera crescente (permissão `erp.send`) |
| `POST` | `/api/ocr/classify-text` | Classificar texto (heurística) |
| `POST` | `/api/ocr/process` | Processar documento (legado) |

#### Configurações

| Método | Endpoint | Descrição |
|---|---|---|
| `GET/PATCH` | `/api/ocr/settings/integrations` | Configurações de integração |
| `GET/PATCH` | `/api/ocr/settings/ocr` | Configurações de OCR |
| `GET/PATCH` | `/api/ocr/settings/email` | Configurações de e-mail |
| `GET/POST` | `/api/ocr/schema-configs` | Schemas de extração |
| `GET/PATCH` | `/api/ocr/schema-configs/<uuid>` | Detalhe do schema |
| `GET/POST` | `/api/ocr/layout-configs` | Configurações de layout |

#### Operações

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/ocr/engines` | Engines de OCR disponíveis |

#### Autenticação

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/auth/login` | Login (e-mail + senha) |
| `POST` | `/api/auth/logout` | Logout (blacklist token) |
| `POST` | `/api/auth/refresh` | Renovar access token |
| `POST` | `/api/auth/register` | Registrar usuário |
| `GET` | `/api/auth/me` | Dados do usuário logado |

#### Usuários / Roles

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/auth/permissions` | Listar permissões |
| `GET/POST` | `/api/auth/roles` | Listar / criar roles |
| `GET/PATCH/DELETE` | `/api/auth/roles/<uuid>` | Detalhe da role |
| `GET/POST` | `/api/auth/users` | Listar / criar usuários |
| `GET/PATCH` | `/api/auth/users/<id>` | Detalhe do usuário |

#### Saúde

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/ocr/health` | Health check |
| `GET` | `/api/ocr/ready` | Readiness check |

### Management Commands

```bash
python manage.py migrate              # Aplicar migrations
python manage.py seed_permissions     # Criar permissões padrão
python manage.py seed_admin           # Criar usuário admin
python manage.py erp_live_writes --tenant <slug> --enable --confirm <slug>  # Habilitar o envio real ao Superlógica (por tenant)
python manage.py import_legacy_sqlite # Importar dados legados
python manage.py sweep_stuck_documents [--older-than-minutes 30] [--tenant <slug>] [--dry-run]
                                      # Marca como falhos documentos parados no processamento
```

### Processamento em segundo plano e conexão com o banco

O upload dispara o OCR e a extração num pool de threads dentro do próprio processo
(`documents/services/processing_queue.py`, `DOCUPARSE_PROCESSING_WORKERS`, default 2).
Regras para qualquer thread de fundo que usa o ORM:

- Rodar a tarefa dentro de `_with_fresh_connection`, ou chamar `close_old_connections()`
  no início e `connection.close()` no fim. O Django só renova conexões no ciclo HTTP;
  sem isso, depois de um restart do Postgres toda tarefa falha com a conexão morta.
- Capturar as exceções com `logger.exception`. O `Future` do executor não é lido por
  ninguém, e uma exceção que fica nele não aparece no log.
- Se o processamento falhar, um documento em `RECEIVED` vai para `OCR_FAILED`, com o
  motivo em `metadata.processing_error`, e pode ser reprocessado.

**Varredura de documentos parados.** Se o pod morrer no meio do processamento, o documento
fica em `RECEIVED` e o run do orquestrador fica `RUNNING`. Um run `RUNNING` faz o retry
manual do dashboard recusar a operação. O comando `sweep_stuck_documents` corrige os dois:
fecha como `FAILED` os runs `RUNNING` mais antigos que o limite e marca como `OCR_FAILED`
os documentos em `RECEIVED` sem alteração nesse período e sem run recente. Agende-o no k3s:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: docuparser-core-sweep-stuck
spec:
  schedule: "*/10 * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      backoffLimit: 0
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: sweep
              image: <mesma imagem do docuparser-core>
              envFrom: [<mesmo env/secrets do docuparser-core>]
              command: ["python", "manage.py", "sweep_stuck_documents", "--older-than-minutes", "30"]
```

O limite precisa ser maior que o tempo normal de um documento na fila mais o tempo de
processamento. Se houver muitos uploads de uma vez e só 2 workers, aumente o limite.

---

## Serviço de Captura (`backend-com`)

### Tecnologia

| Item | Valor |
|---|---|
| Framework | FastAPI 0.136.0 |
| Arquitetura | Modular "Atoms" |
| Porta | 8070 |

### Endpoints

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/v1/documents/manual` | Upload manual de arquivo |
| `POST` | `/api/v1/email/webhook` | Webhook de e-mail (com validação de assinatura) |
| `POST` | `/api/v1/email/messages` | Integração IMAP |
| `POST` | `/api/v1/email/poll` | Polling IMAP manual |
| `POST` | `/api/v1/whatsapp/webhook` | Webhook Twilio/WhatsApp |
| `POST` | `/api/v1/whatsapp/poll` | Polling WhatsApp manual |
| `GET` | `/health` | Health check |

Após receber um documento, o `backend-com` publica um `document.received` via HTTP POST para `BACKEND_CORE_DOCUMENT_RECEIVED_URL`.

---

## Serviço de OCR (`backend-ocr`)

### Tecnologia

| Item | Valor |
|---|---|
| Framework | FastAPI 0.115.0 |
| Porta | 8080 |

### Engines de OCR disponíveis

| Engine | Uso |
|---|---|
| Docling | PDFs digitais (alta qualidade) |
| OpenRouter (Qwen, DeepSeek, Gemini) | Visão computacional via API |
| Tesseract | Fallback gratuito |
| PaddleOCR | Multi-idioma |
| EasyOCR | Deep learning OCR |

### Endpoints

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/v1/documents/process` | Processar documento com OCR |
| `GET` | `/api/v1/engines` | Listar engines disponíveis |
| `GET` | `/health` | Health check |

---

## Serviço de Extração (`langextract-service`)

### Tecnologia

| Item | Valor |
|---|---|
| Framework | FastAPI 0.115.0 |
| Porta | 8091 |
| LLM padrão | `deepseek/deepseek-chat-v3-0324:free` (via OpenRouter) |

### Endpoints

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/v1/extract` | Extrair campos estruturados de texto |
| `GET` | `/health` | Health check |

### Como funciona a extração

1. Recebe `raw_text` + `schema_definition` (campos esperados)
2. Envia para o LLM via OpenRouter com prompt estruturado
3. Retorna `fields` (JSON com valores extraídos) + `confidence`

### Seleção automática de schema (backend-core)

A função `_resolve_schema_for_extraction()` em `ocr_processor.py` segue a hierarquia:

1. `LayoutConfig` pelo `document.layout` explícito (configuração do admin)
2. Classificador de texto (`_classify_raw_text`) — detecta nota fiscal, boleto, conta de água
3. `LayoutConfig` pelo `document_type` (fallback)

---

## Banco de Dados

### Tecnologia

| Item | Valor |
|---|---|
| SGBD | PostgreSQL 16 |
| ORM | Django ORM |
| Migrations | Django Migrations |

### Entendendo as formas de acesso

> **Importante**: o PostgreSQL **não é um servidor web**. Tentar abri-lo no navegador pelo endereço `http://localhost:5432` não funciona — essa porta usa o protocolo proprietário do Postgres, não HTTP. Para visualizar o banco você precisa de uma ferramenta cliente.

O projeto já inclui o **pgAdmin**, uma ferramenta de administração do PostgreSQL com interface web, que sobe junto com os demais serviços via Docker Compose.

---

### Opção 1 — pgAdmin (via navegador, recomendado)

O pgAdmin é um painel web para explorar e consultar o banco de dados. Ele já faz parte do `docker-compose.yml` e **sobe automaticamente** com os demais serviços.

#### Passo a passo

**1. Suba os serviços normalmente:**

```bash
cd docuparse-project/
sudo docker compose up --build
```

**2. Acesse o pgAdmin no navegador:**

```
http://localhost:5050
```

**3. Faça login com as credenciais padrão:**

| Campo | Valor |
|---|---|
| E-mail | `admin@docuparse.com` |
| Senha | `admin123` |

**4. Registre o servidor do banco de dados:**

Ao entrar pela primeira vez, o pgAdmin estará vazio. Você precisa conectá-lo ao PostgreSQL que está rodando no Docker:

- No menu lateral, clique com o botão direito em **Servers** → **Register** → **Server...**
- Na aba **General**: dê um nome ao servidor, por exemplo `docuparse-local`
- Na aba **Connection**, preencha:

| Campo | Valor |
|---|---|
| Host name/address | `postgres` |
| Port | `5432` |
| Maintenance database | `docuparse` |
| Username | `docuparse` |
| Password | `docuparse` |

> **Por que `postgres` e não `localhost`?** Porque o pgAdmin e o PostgreSQL estão na mesma rede Docker interna (`docuparse-network`). Dentro dessa rede, o banco é identificado pelo nome do serviço `postgres`, e não por `localhost`.

- Clique em **Save**. O servidor aparecerá no painel lateral.

**5. Navegue pelas tabelas:**

```
Servers
  └── docuparse-local
        └── Databases
              └── docuparse
                    └── Schemas
                          └── public
                                └── Tables
```

Clique em qualquer tabela com o botão direito → **View/Edit Data** → **All Rows** para visualizar os dados.

---

### Opção 2 — Terminal (psql)

```bash
# Abrir console SQL diretamente no container (sem instalar nada localmente)
sudo docker compose exec postgres psql -U docuparse -d docuparse
```

Comandos úteis dentro do `psql`:

```sql
\dt                        -- listar todas as tabelas
\d documents_document      -- ver colunas da tabela
\q                         -- sair

-- Exemplos de consultas
SELECT id, original_filename, status FROM documents_document ORDER BY created_at DESC LIMIT 10;
SELECT * FROM users_permission;
```

---

### Opção 3 — Cliente externo (DBeaver, TablePlus, DataGrip)

Se preferir usar um cliente instalado na sua máquina, configure a conexão apontando para `localhost`:

| Parâmetro | Valor padrão |
|---|---|
| Host | `localhost` |
| Porta | `5432` |
| Banco | `docuparse` |
| Usuário | `docuparse` |
| Senha | `docuparse` |

> Os valores são configuráveis via variáveis `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` no `.env`.

---

## Estrutura do Banco de Dados

### `documents_tenant`

Representa uma organização (tenant) no sistema multi-tenant.

| Campo | Tipo | Nullable | PK | FK | Descrição |
|---|---|---|---|---|---|
| id | UUID | Não | Sim | — | Identificador único |
| slug | SlugField(50) | Não | — | — | Identificador legível único |
| name | CharField(255) | Não | — | — | Nome da organização |
| is_active | Boolean | Não | — | — | Ativo/inativo |
| created_at | DateTimeField | Não | — | — | Data de criação |
| updated_at | DateTimeField | Não | — | — | Última atualização |

```sql
SELECT * FROM documents_tenant LIMIT 10;
SELECT * FROM documents_tenant WHERE slug = 'tenant-demo';
```

---

### `documents_document`

Documento recebido e seu status no pipeline.

| Campo | Tipo | Nullable | PK | FK | Descrição |
|---|---|---|---|---|---|
| id | UUID | Não | Sim | — | Identificador único |
| tenant_id | UUID | Não | — | tenant | Organização dona |
| status | CharField(64) | Não | — | — | Status do pipeline |
| channel | CharField(32) | Não | — | — | Canal de entrada (manual, email, whatsapp) |
| file_uri | CharField(1024) | Não | — | — | Caminho do arquivo no storage |
| raw_text_uri | CharField(1024) | Sim | — | — | Caminho do texto extraído pelo OCR |
| original_filename | CharField(255) | Sim | — | — | Nome original do arquivo |
| content_type | CharField(128) | Sim | — | — | MIME type (application/pdf, etc.) |
| size_bytes | BigInteger | Não | — | — | Tamanho do arquivo |
| sha256 | CharField(64) | Sim | — | — | Hash do arquivo |
| document_type | CharField(64) | Sim | — | — | Tipo detectado pelo OCR (digital_pdf, scanned_image, etc.) |
| layout | CharField(128) | Sim | — | — | Layout explícito (normalmente vazio) |
| correlation_id | UUID | Não | — | — | ID de correlação para rastreamento |
| received_at | DateTimeField | Não | — | — | Data de recebimento |
| metadata | JSONField | Não | — | — | Metadados extras |
| created_at | DateTimeField | Não | — | — | Data de criação |
| updated_at | DateTimeField | Não | — | — | Última atualização |

**Status possíveis:**

| Status | Descrição |
|---|---|
| RECEIVED | Recebido, aguardando OCR |
| OCR_COMPLETED | Texto extraído com sucesso |
| OCR_FAILED | Falha no OCR |
| LAYOUT_CLASSIFIED | Layout classificado |
| EXTRACTION_COMPLETED | Campos extraídos |
| VALIDATION_PENDING | Aguardando validação humana |
| APPROVED | Aprovado pelo operador |
| REJECTED | Rejeitado pelo operador |
| ERP_INTEGRATION_REQUESTED | Exportação para ERP solicitada |
| ERP_SENT | Enviado ao ERP com sucesso |
| ERP_FAILED | Falha no envio ao ERP |

```sql
SELECT id, original_filename, status, created_at FROM documents_document ORDER BY created_at DESC LIMIT 20;
SELECT * FROM documents_document WHERE status = 'VALIDATION_PENDING';
SELECT * FROM documents_document WHERE tenant_id = (SELECT id FROM documents_tenant WHERE slug = 'tenant-demo');
```

---

### `documents_extractionresult`

Resultado da extração de campos de um documento.

| Campo | Tipo | Nullable | PK | FK | Descrição |
|---|---|---|---|---|---|
| id | UUID | Não | Sim | — | Identificador único |
| document_id | UUID | Não | — | document (1:1) | Documento pai |
| schema_id | CharField(128) | Não | — | — | ID do schema usado (ex: `nota_fiscal_default`) |
| schema_version | CharField(32) | Não | — | — | Versão do schema |
| fields | JSONField | Não | — | — | Campos extraídos (valor + confiança) |
| confidence | Float | Não | — | — | Confiança geral (0.0–1.0) |
| requires_human_validation | Boolean | Não | — | — | Se precisa de revisão humana |
| created_at | DateTimeField | Não | — | — | Data de criação |
| updated_at | DateTimeField | Não | — | — | Última atualização |

```sql
SELECT d.original_filename, e.schema_id, e.confidence, e.fields
FROM documents_extractionresult e
JOIN documents_document d ON d.id = e.document_id
ORDER BY e.created_at DESC LIMIT 10;
```

---

### `documents_validationdecision`

Decisão tomada por um operador sobre um documento.

| Campo | Tipo | Nullable | PK | FK | Descrição |
|---|---|---|---|---|---|
| id | UUID | Não | Sim | — | Identificador único |
| document_id | UUID | Não | — | document | Documento avaliado |
| decided_by_id | Integer | Não | — | auth_user | Usuário que decidiu |
| decision | CharField(32) | Não | — | — | approved / rejected / corrected |
| corrected_fields | JSONField | Sim | — | — | Campos corrigidos pelo operador |
| notes | TextField | Sim | — | — | Observações |
| created_at | DateTimeField | Não | — | — | Data da decisão |

```sql
SELECT d.original_filename, v.decision, v.notes, v.created_at
FROM documents_validationdecision v
JOIN documents_document d ON d.id = v.document_id
ORDER BY v.created_at DESC LIMIT 20;
```

---

### `documents_schemaconfig`

Schema de extração de campos (define quais campos extrair).

| Campo | Tipo | Nullable | PK | FK | Descrição |
|---|---|---|---|---|---|
| id | UUID | Não | Sim | — | Identificador único |
| tenant_id | UUID | Não | — | tenant | Organização dona |
| schema_id | CharField(128) | Não | — | — | Identificador do schema (ex: `nota_fiscal_default`) |
| version | CharField(32) | Não | — | — | Versão do schema |
| definition | JSONField | Não | — | — | Definição dos campos esperados |
| is_active | Boolean | Não | — | — | Ativo/inativo |

```sql
SELECT schema_id, version, is_active FROM documents_schemaconfig;
```

---

### `documents_layoutconfig`

Associa um tipo de layout/documento a um schema de extração.

| Campo | Tipo | Nullable | PK | FK | Descrição |
|---|---|---|---|---|---|
| id | UUID | Não | Sim | — | Identificador único |
| tenant_id | UUID | Não | — | tenant | Organização dona |
| schema_config_id | UUID | Não | — | schemaconfig | Schema associado |
| layout | CharField(128) | Não | — | — | Chave do layout |
| document_type | CharField(64) | Não | — | — | Tipo de documento OCR |
| confidence_threshold | Float | Não | — | — | Limiar de confiança |
| is_active | Boolean | Não | — | — | Ativo/inativo |

```sql
SELECT lc.layout, lc.document_type, sc.schema_id
FROM documents_layoutconfig lc
JOIN documents_schemaconfig sc ON sc.id = lc.schema_config_id;
```

---

### `users_role`

Papel de acesso com permissões associadas.

| Campo | Tipo | Nullable | PK | FK | Descrição |
|---|---|---|---|---|---|
| id | UUID | Não | Sim | — | Identificador único |
| name | CharField(128) | Não | — | — | Nome da role (único) |
| created_at | DateTimeField | Não | — | — | Data de criação |

### `users_permission`

Permissão granular do sistema.

| Campo | Tipo | Nullable | PK | FK | Descrição |
|---|---|---|---|---|---|
| id | UUID | Não | Sim | — | Identificador único |
| code | CharField(64) | Não | — | — | Código único (ex: `documents.send`) |
| description | CharField(255) | Não | — | — | Nome legível |

**Permissões disponíveis:**

| Código | Descrição |
|---|---|
| `inbox.view` | Visualizar Inbox |
| `documents.send` | Enviar Documentos |
| `documents.validate` | Validar Documentos |
| `models.create` | Criar Modelos |
| `models.edit` | Editar Modelos |
| `operations.access` | Dashboard de processos e retry de etapas |
| `users.manage` | Gerenciar Usuários |
| `roles.manage` | Gerenciar Roles |

```sql
SELECT * FROM users_permission;
SELECT r.name, p.code FROM users_role r
JOIN users_role_permissions rp ON rp.role_id = r.id
JOIN users_permission p ON p.id = rp.permission_id
ORDER BY r.name, p.code;
```

---

### `documents_userprofile`

Vínculo entre o usuário Django e uma organização (tenant) + role.

| Campo | Tipo | Nullable | PK | FK | Descrição |
|---|---|---|---|---|---|
| id | UUID | Não | Sim | — | Identificador único |
| user_id | Integer | Não | — | auth_user | Usuário Django |
| tenant_id | UUID | Não | — | tenant | Organização |
| role_ref_id | UUID | Sim | — | users_role | Role do usuário |

```sql
SELECT u.username, u.email, t.slug AS tenant, r.name AS role
FROM documents_userprofile up
JOIN auth_user u ON u.id = up.user_id
JOIN documents_tenant t ON t.id = up.tenant_id
LEFT JOIN users_role r ON r.id = up.role_ref_id;
```

---

## Eventos e Mensageria

O processamento de documentos **não** passa pelo barramento: o backend-core chama o backend-ocr e o
langextract-service por HTTP, em processo (ver "Processamento em segundo plano"). O pipeline antigo por
Redis Streams (workers de OCR, layout e extração e o `consume_events` do core) e o Camunda foram
removidos em 11/2026.

O barramento (Redis Streams, com fallback para arquivos locais em desenvolvimento) continua recebendo
os eventos abaixo. Os eventos de ERP também são usados como mensagens dentro do próprio core.

### Eventos disponíveis

| Evento | Publicado por | Consumido por |
|---|---|---|
| `document.received` | backend-com | ninguém no barramento (o mesmo payload vai ao core por HTTP, `BACKEND_CORE_DOCUMENT_RECEIVED_URL`) |
| `erp.integration.requested` | backend-core | backend-core (conector do ERP, em processo, com o tenant) |
| `erp.sent` | backend-core | backend-core |
| `erp.failed` | backend-core | backend-core |
| `erp.send.confirmed` | backend-core | histórico do documento (quem confirmou o envio e quando) |
| `erp.send.retried` | backend-core | histórico do documento (quem repetiu o envio e quando) |
| `erp.dry_run` | backend-core | histórico do documento (simulação: nada foi enviado ao ERP) |

---

## Observabilidade e Rastreamento Distribuído

O sistema usa **OpenTelemetry** para rastreamento distribuído (tracing) entre todos os processos de runtime: `backend-com`, `backend-core`, `backend-ocr`, `langextract-service` e `frontend`. O objetivo é reconstruir, por um único `trace_id`, o caminho completo — síncrono e assíncrono — que uma requisição percorre entre serviços.

### Componentes

- **OTel Collector** (`otel/opentelemetry-collector-contrib`, serviço `otel-collector` no `docker-compose.yml`): recebe spans via OTLP (gRPC `:4317` / HTTP `:4318`) de todos os serviços, aplica redação básica de atributos e *tail sampling*, e exporta para o Jaeger. Nenhum serviço de aplicação fala diretamente com o Jaeger — trocar o backend de armazenamento no futuro (Grafana Tempo, Honeycomb, etc.) é apenas mudança de configuração do Collector.
- **Jaeger** (`jaegertracing/all-in-one`, serviço `jaeger`): armazenamento e UI de visualização de traces, `http://localhost:16686`.

### Bootstrap

Cada serviço Python chama `configure_tracing(service_name)` (`shared/docuparse_observability/tracing.py`) uma única vez no bootstrap, o que cria um `TracerProvider` com `Resource` (`service.name`, `service.version`, `deployment.environment`), habilita a instrumentação automática relevante (`FastAPIInstrumentor`/`DjangoInstrumentor`, `RequestsInstrumentor`/`HTTPXClientInstrumentor`, `RedisInstrumentor`) e registra:

1. `RedactingSpanProcessor` — remove/mascara atributos sensíveis (corpo de request/response, `Authorization`, chaves `_token`/`_secret`/`_password`) antes de qualquer exportação.
2. `BatchSpanProcessor` com exporter OTLP de timeout curto (1-2s) — exportação sempre assíncrona/não-bloqueante: se o Collector estiver indisponível, spans são descartados em background, sem afetar a resposta ao usuário.

O frontend usa o equivalente em JS (`frontend/src/shared/lib/tracing.ts`, `@opentelemetry/sdk-trace-web`), inicializado em `frontend/src/app/main.tsx`.

### Propagação através das fronteiras assíncronas

- **HTTP síncrono**: cabeçalho `traceparent`/`tracestate` (W3C Trace Context), propagado automaticamente pelas instrumentações de cliente HTTP.
- **Eventos (Redis Streams)**: campo `trace_context: dict[str, str] | None` no schema base de evento (`contracts/events/schemas.py`), populado na publicação (`EventBus.publish()`) e usado no consumo para criar um `Span Link` (não parent-child, para não inflar a duração aparente do span de origem através da espera na fila).
- **Threads de fundo do core**: `capture_current_span_link()` guarda o contexto da requisição e a thread do pool inicia seu span com um `Link` para ele.

### Redação e segurança de dados sensíveis

Nenhum atributo de span pode conter conteúdo de documento, dado pessoal ou credencial. Isso é garantido em duas camadas: o `RedactingSpanProcessor` (em processo, antes da exportação) e uma allowlist estrita no `otel-collector-config.yaml` (defesa em profundidade — qualquer atributo fora da allowlist é descartado no Collector, mesmo que escape da primeira camada).

### Amostragem (tail sampling)

O Collector aplica `tailsamplingprocessor` (`otel-collector-config.yaml`) com duas políticas avaliadas em OR:

1. Retém **100%** dos traces com qualquer span em status `ERROR`.
2. Retém uma fração probabilística configurável do restante, via `OTEL_TAIL_SAMPLING_PERCENTAGE` (padrão `100` em dev; reduzir em produção para controlar volume sem nunca perder um trace com erro).

### Correlação com logs

`log_event()` (`shared/docuparse_observability/__init__.py`) anexa automaticamente `trace_id`/`span_id` do span ativo, quando existir, permitindo saltar de um log de erro para o trace completo no Jaeger.

### Variáveis de ambiente

| Variável | Onde é usada | Descrição |
|---|---|---|
| `USE_TELEMETRY` | Todos os serviços (exceto `otel-collector`) | Liga/desliga o tracing (`configure_tracing()` e as instrumentações de biblioteca). Padrão `false` — só ativa exportação/instrumentação quando setada como `true`/`1`/`yes`/`on`. Permite rodar sem um Collector disponível (ex.: servidores onde ele ainda não foi instalado). O `docker-compose.yml` local seta `true` por padrão, já que sobe o `otel-collector` junto |
| `OTEL_SERVICE_NAME` | Todos os serviços | Nome do serviço no atributo de resource `service.name` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Todos os serviços | Endpoint do Collector (padrão `http://otel-collector:4317`) |
| `DEPLOYMENT_ENVIRONMENT` | Todos os serviços | Popula `deployment.environment` (dev/staging/production) |
| `OTEL_TAIL_SAMPLING_PERCENTAGE` | `otel-collector` | % de traces sem erro retidos pelo tail sampling (padrão `100`) |

Ver `docs/specs/020-opentelemetry-tracing/quickstart.md` para o passo a passo completo de validação local (subir o stack, disparar uma requisição, localizar o trace no Jaeger, validar resiliência e ausência de dados sensíveis).

---

## Autenticação e Permissões

### JWT

| Parâmetro | Valor |
|---|---|
| Access token lifetime | 15 minutos |
| Refresh token lifetime | 7 dias |
| Rotação de refresh tokens | Ativada |
| Blacklist após rotação | Ativada |

### Fluxo de autenticação

1. `POST /api/auth/login` com `{ "email": "...", "password": "..." }`
2. Resposta: `{ "access": "<token>", "refresh": "<token>", "user": {...} }`
3. Incluir no header: `Authorization: Bearer <access_token>`
4. Renovar com `POST /api/auth/refresh` usando o `refresh` token

### Modelo de permissões

```
auth_user (Django built-in)
    └── documents_userprofile
            ├── tenant   (organização)
            └── role_ref → users_role
                              └── permissions (M2M) → users_permission
```

O front-end verifica permissões via `GET /api/auth/me` que retorna o perfil completo com a lista de `permissions[]`.

---

## Variáveis de Ambiente

Arquivo: `docuparse-project/.env`

### Banco de Dados

| Variável | Padrão | Descrição |
|---|---|---|
| `POSTGRES_DB` | `docuparse` | Nome do banco |
| `POSTGRES_USER` | `docuparse` | Usuário |
| `POSTGRES_PASSWORD` | `docuparse` | Senha |
| `POSTGRES_HOST` | `postgres` | Host (nome do serviço Docker) |
| `POSTGRES_PORT` | `5432` | Porta |

### Redis

| Variável | Padrão | Descrição |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/0` | URL de conexão |

### MinIO (Object Storage)

| Variável | Padrão | Descrição |
|---|---|---|
| `MINIO_ROOT_USER` | `docuparse` | Usuário root |
| `MINIO_ROOT_PASSWORD` | `docuparse-local` | Senha root |

### LLM / OCR

| Variável | Padrão | Descrição |
|---|---|---|
| `OPENROUTER_API_KEY` | — | Chave da API OpenRouter (obrigatória para OCR e extração) |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | URL base da API |
| `OPENROUTER_MODEL` | `qwen/qwen2.5-vl-72b-instruct` | Modelo de visão para OCR |
| `OPENROUTER_FALLBACK_MODEL` | `qwen/qwen2.5-vl-72b-instruct` | Modelo fallback |
| `LANGEXTRACT_MODEL` | `deepseek/deepseek-chat-v3-0324:free` | Modelo de texto para extração |

### Admin

| Variável | Padrão | Descrição |
|---|---|---|
| `DOCUPARSE_ADMIN_EMAIL` | `admin@docuparse.com` | E-mail do admin inicial |
| `DOCUPARSE_ADMIN_PASSWORD` | `admin123` | Senha do admin inicial |
| `DOCUPARSE_ADMIN_USERNAME` | `admin` | Username do admin inicial |

### Escrita no Superlógica

A despesa de um documento aprovado é lançada no Superlógica pelo pacote `erp_export`
(separado de `erp_import`, que só lê). Os tokens do tenant são de um ambiente real, então
**todo padrão é o mais seguro**: nada é enviado sem que as travas abaixo permitam.

| Modo (`superlogica_mode`) | O que faz |
|---|---|
| `disabled` (padrão) | Não integra. A aprovação só registra o pedido, como sempre. |
| `mock` | Responde com um `external_id` falso, sem rede. A aprovação integra sozinha. |
| `sandbox` | Envia a um ambiente de teste. O analista confirma antes do primeiro envio. |
| `live` | Envia ao Superlógica de produção. Mesma confirmação do analista. |

Travas, todas obrigatórias para um envio real:

- **`superlogica_dry_run`** (ligado por padrão): monta e valida a despesa e não envia. Fica na tela de integrações.
- **Sandbox:** só envia a um host listado em `SUPERLOGICA_SANDBOX_HOSTS` (vazio por padrão) e nunca ao host de produção.
- **Live:** exige a habilitação do tenant (`erp_live_writes`, nunca pela API), `SUPERLOGICA_LIVE_WRITES=1` no servidor e o contrato de escrita verificado em ambiente de teste (`erp_export/payload.py: CONTRACT_VERIFIED`, hoje `False`).
- O escritor só conhece um endpoint de escrita (`POST despesas`), nunca repete um POST sozinho e nunca registra token nem corpo.

| Variável | Padrão | Descrição |
|---|---|---|
| `SUPERLOGICA_SANDBOX_HOSTS` | vazio | Hosts autorizados para o modo `sandbox`, separados por vírgula |
| `SUPERLOGICA_LIVE_WRITES` | desligado | `1` libera o envio real no servidor (ainda exige a habilitação do tenant) |

O conector roda em processo (fila de segundo plano do core, como OCR e extração), sem depender
de um worker de eventos. Antes de enviar ele consulta o ERP (só leitura): o fornecedor precisa
existir e não pode haver despesa com o mesmo fornecedor, valor e vencimento. Se a resposta de um
envio se perder, a próxima tentativa acha a despesa no ERP e marca como enviada, sem reenviar.

### Processamento automático

| Variável | Padrão | Descrição |
|---|---|---|
| `DOCUPARSE_AUTO_PROCESS_OCR` | `true` | Disparar OCR automaticamente ao receber documento |
| `DOCUPARSE_AUTO_PROCESS_EXTRACTION` | `true` | Disparar extração automaticamente após OCR |
| `PAYMENT_MATCH_WINDOW_HOURS` | `72` | Janela, em horas antes e depois do recebimento, em que NF e boleto são candidatos a match |

### Segurança

| Variável | Padrão | Descrição |
|---|---|---|
| `DOCUPARSE_INTERNAL_SERVICE_TOKEN` | — | Token Bearer para comunicação entre serviços |
| `DOCUPARSE_EMAIL_WEBHOOK_TOKEN` | — | Token para validar webhooks de e-mail |
| `DOCUPARSE_WHATSAPP_WEBHOOK_TOKEN` | — | Token para validar webhooks WhatsApp |

### Integração E-mail (IMAP)

| Variável | Descrição |
|---|---|
| `imap_reader_host` | Host IMAP (ex: `imap.gmail.com`) |
| `imap_reader_username` | Usuário da conta de e-mail |
| `imap_reader_password` / `DOCUPARSE_IMAP_PASSWORD` | Senha da conta IMAP |
| `imap_reader_port` | Porta IMAP (padrão: `993`) |
| `imap_reader_folder` | Pasta a monitorar (padrão: `INBOX`) |

### Integração WhatsApp (Twilio)

| Variável | Descrição |
|---|---|
| `TWILIO_ACCOUNT_SID` | Account SID do Twilio |
| `TWILIO_AUTH_TOKEN` | Auth Token do Twilio |
| `TWILIO_API_KEY_SID` | API Key SID |
| `TWILIO_API_KEY_SECRET` | API Key Secret |
