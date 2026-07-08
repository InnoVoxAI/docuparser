# Feature 011 — Armazenamento de objetos compartilhado (S3/MinIO)

Guia operacional da feature: o que foi feito, como subir a aplicação, como acessar e validar os serviços, quais variáveis de ambiente configurar (dev × produção) e como voltar ao modo antigo.

> Documentos de projeto relacionados: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

---

## 1. O que foi feito (resumo)

Antes, cada serviço gravava/lia arquivos no **disco local do próprio pod**. Em pods isolados (staging/produção), um arquivo gravado por um serviço não existia no disco dos outros → o endpoint de arquivo retornava 404 e o OCR falhava.

Esta feature substitui isso por um **storage de objetos compartilhado, compatível com S3/MinIO**, mantendo o comportamento antigo como default:

- Novo pacote `docuparse_storage` com `S3Storage`, `RoutingStorage` e a fábrica **`get_storage()`** (único ponto de instanciação).
- **Seleção por ambiente**: `DOCUPARSE_STORAGE_BACKEND` (`local` = comportamento antigo, default; `s3` = storage compartilhado).
- **Leitura por esquema da URI** (`local://` vs `s3://`): referências antigas continuam legíveis → migração incremental e rollback sem perda de acesso.
- **Falhas explícitas**: objeto inexistente → 404/`FileNotFoundError`; indisponibilidade/credencial → erro propagado (nunca um documento sem arquivo).
- Todos os serviços de I/O (com, core, ocr, layout, langextract) passaram a usar `get_storage()`; correção do ponto que burlava a abstração no `layout-service`.
- Script de migração idempotente: `docuparse-project/scripts/migrate_storage_local_to_s3.py`.
- No `docker-compose.yml`: serviço `minio` (portas do host **9002/9003** para evitar conflito com outros MinIO locais), `minio-setup` que cria o bucket, e as envs de storage ligadas em todos os serviços.

---

## 2. Passo a passo para subir a aplicação

A partir de `docuparse-project/`:

```bash
cd ~/repositories/docuparser/docuparse-project

# 0) Na primeira vez, crie seu .env local a partir do exemplo.
#    O compose EXIGE MINIO_ROOT_USER/MINIO_ROOT_PASSWORD (sem default) — sem
#    .env ele falha com uma mensagem clara. O .env é gitignored (não versionado).
cp -n .env.example .env

# 1) Limpe containers/órfãos de execuções anteriores do stack
sudo docker compose -f docker-compose.yml down --remove-orphans

# 2) Suba o stack
sudo docker compose -f docker-compose.yml up
```

Ordem esperada na subida: `postgres`, `redis`, `minio` sobem → `minio-setup` cria o bucket `docuparse` e encerra → os backends sobem → `frontend`.

> **Conflito de porta 9000 (`port is already allocated`)?** Já tratado: o MinIO do docuparse usa **9002/9003** no host. Se ainda ocorrer, há outro container publicando a porta — verifique com `docker ps --filter publish=9002` (com e sem `sudo`, pois daemons rootless e rootful são independentes).

---

## 3. Como acessar (portas no host)

| Componente | URL / porta (host) | Porta interna | Observação |
|---|---|---|---|
| **Frontend** | http://localhost:5173 | 5173 | UI (Vite dev server) |
| **Backend Core** (Django) | http://localhost:8000 | 8000 | API `/api/ocr`, `/api/auth` |
| **Backend Com** (FastAPI) | http://localhost:8070 | 8070 | ingestão / upload manual |
| **Backend OCR** | http://localhost:8080 | 8080 | |
| **Layout Service** | http://localhost:8090 | 8090 | |
| **LangExtract Service** | http://localhost:8091 | 8091 | |
| **MinIO — API S3** | http://localhost:9002 | 9000 | endpoint S3 (uso interno: `http://minio:9000`) |
| **MinIO — Console** | http://localhost:9003 | 9001 | login `docuparse` / `docuparse-local` |
| **PostgreSQL** | localhost:5432 | 5432 | user/db/senha `docuparse` (default) |
| **Redis** | localhost:6380 | 6379 | event bus |

> Importante: os serviços conversam com o MinIO **pela rede interna** em `http://minio:9000`. As portas 9002/9003 são só para você acessar do host/navegador; remapeá-las **não** afeta a aplicação.

### 3.1 Login no console do MinIO

Abra **http://localhost:9003** e use as credenciais root do MinIO (mesmas de `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`):

| Campo | Valor (default local) |
|---|---|
| **Username** | `docuparse` |
| **Password** | `docuparse-local` |

Depois de logar, o bucket dos artefatos é o **`docuparse`** (em *Object Browser* → `docuparse` → `documents/...`).

> Se você sobrescreveu `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` no `.env`, use os valores que você definiu. Em produção, as credenciais vêm de Secret e **não** são as de dev.

### 3.2 Acessando de uma máquina remota (servidor via SSH/VS Code)

Se a aplicação roda em um **servidor remoto** (você acessa por SSH), `http://localhost:9003` no seu navegador aponta para a *sua* máquina, não para o servidor. As portas ficam publicadas **no servidor**. Para alcançá-las do seu navegador local, encaminhe as portas:

- **VS Code Remote-SSH (mais fácil)**: aba **PORTS** → *Forward a Port* → adicione `9003` (e `9002`, `5173`). Clique no link `localhost:9003` gerado.
- **Túnel SSH manual** (rode na **sua** máquina local, com o host que você usa para conectar — não o hostname interno do servidor):
  ```bash
  ssh -L 9003:localhost:9003 -L 9002:localhost:9002 -L 5173:localhost:5173 <seu-host-ssh>
  ```
  Se alguma porta local já estiver em uso, mapeie para outra (ex.: `-L 19003:localhost:9003` e acesse `http://localhost:19003`).

Acesso rápido ao banco:
```bash
sudo docker compose exec postgres psql -U docuparse -d docuparse
```

---

## 4. Como confirmar que está funcionando

### 4.1 Estado dos containers
```bash
sudo docker compose ps
```
Espere `postgres`, `redis`, `minio` como **healthy**; `minio-setup` como **exited (0)**; os backends **running/healthy**.

### 4.2 Health dos backends
```bash
curl -fsS http://localhost:8000/api/ocr/health && echo   # backend-core
curl -fsS http://localhost:8070/health        && echo   # backend-com
curl -fsS http://localhost:8080/health        && echo   # backend-ocr
curl -fsS http://localhost:8090/health        && echo   # layout-service
curl -fsS http://localhost:8091/health        && echo   # langextract-service
```

### 4.3 MinIO / S3
- Bucket criado: abra o console em **http://localhost:9003** e confirme o bucket **`docuparse`**.
- Fim-a-fim: envie um documento pela UI (http://localhost:5173) e verifique que os objetos apareceram no bucket:
  ```
  documents/{tenant}/{document_id}/original
  documents/{tenant}/{document_id}/ocr/raw_text.json
  ```
- Confirme que o backend gravou como `s3://` (e não `local://`):
  ```bash
  sudo docker compose exec postgres psql -U docuparse -d docuparse \
    -c "select file_uri, raw_text_uri from documents_document order by created_at desc limit 3;"
  ```
  As URIs devem começar com `s3://docuparse/...`. Se aparecer `local://`, o backend `s3` **não** está ativo (revise as envs).

---

## 5. Variáveis de ambiente

As variáveis são lidas pelo `docker-compose.yml` (interpolação `${VAR:-default}` para os valores não sensíveis) e pelo `docuparse-project/.env`. **As credenciais do MinIO (`MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`) NÃO têm default no compose** — copie `.env.example` para `.env` (`cp .env.example .env`) antes de subir. Os demais valores (bucket, região, endpoint, portas) têm default e só precisam ir no `.env` se quiser sobrescrever.

### 5.1 Novas variáveis desta feature

| Variável | Valor **local** (default do compose) | Valor em **produção** |
|---|---|---|
| `DOCUPARSE_STORAGE_BACKEND` | `s3` (ou `local` p/ modo antigo) | `s3` |
| `S3_ENDPOINT_URL` | `http://minio:9000` (interno) | endpoint real do MinIO/S3 (**vazio** se AWS S3 nativo) |
| `S3_BUCKET` | `docuparse` | bucket **provisionado pela infra** |
| `S3_REGION` | `us-east-1` | região real (ex.: `us-east-1`, `sa-east-1`) |
| `AWS_ACCESS_KEY_ID` | `= MINIO_ROOT_USER` do `.env` | **via Secret** (k8s Secret / Vault) |
| `AWS_SECRET_ACCESS_KEY` | `= MINIO_ROOT_PASSWORD` do `.env` | **via Secret** (k8s Secret / Vault) |

### 5.2 Variáveis auxiliares do MinIO local (só dev)

| Variável | Default | Papel |
|---|---|---|
| `MINIO_ROOT_USER` | do `.env` (ex.: `.env.example` → `docuparse`) | usuário root do MinIO local (obrigatório) |
| `MINIO_ROOT_PASSWORD` | do `.env` (ex.: `.env.example` → `docuparse-local`) | senha root do MinIO local (obrigatório) |
| `MINIO_API_PORT` | `9002` | porta do host → API S3 do MinIO (só dev) |
| `MINIO_CONSOLE_PORT` | `9003` | porta do host → console do MinIO (só dev) |

Em **produção** o MinIO/S3 é gerenciado pela infra: não se usa `MINIO_ROOT_*` nem `MINIO_*_PORT` do compose; o bucket é provisionado fora da aplicação (a app **não** cria bucket em runtime, por design) e as credenciais entram por **Secret**, nunca no código.

### 5.3 Exemplo de `.env` local (opcional — sobrescreve os defaults)

```dotenv
# Storage compartilhado (feature 011)
DOCUPARSE_STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET=docuparse
S3_REGION=us-east-1
MINIO_ROOT_USER=docuparse
MINIO_ROOT_PASSWORD=docuparse-local
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY seguem MINIO_ROOT_USER/PASSWORD por default
```

---

## 6. Como voltar ao modo antigo (local)

O modo `local` é o comportamento histórico (disco/volume compartilhado), preservado sem regressão.

No `docuparse-project/.env`:
```dotenv
DOCUPARSE_STORAGE_BACKEND=local
```
Depois:
```bash
sudo docker compose -f docker-compose.yml up -d
```

Notas:
- Como o `RoutingStorage` resolve por esquema, documentos já gravados em `s3://` **continuam legíveis** enquanto o MinIO estiver de pé (mantenha as credenciais S3 configuradas para lê-los).
- No modo `local`, os serviços compartilham o volume Docker `docuparse-storage` (montado em `/data/storage`), que equivale a um volume compartilhado entre os pods.

### Migração de dados existentes (`local://` → `s3://`)

Rode **dentro do container backend-core** (onde o banco, as credenciais S3 e o volume `/data/storage` com os objetos locais estão disponíveis). Use o **management command** (a pasta `scripts/` não é montada no container):

```bash
sudo docker compose exec backend-core python manage.py migrate_storage_local_to_s3 --dry-run
sudo docker compose exec backend-core python manage.py migrate_storage_local_to_s3 --apply
```

> O script `scripts/migrate_storage_local_to_s3.py` continua existindo para uso fora do container (precisa de `PYTHONPATH` incluindo `shared/` e do ambiente Django/S3). No fluxo Docker, prefira o command acima.

**Um comando, sem cerimônia:** a migração é idempotente e retomável (itens não migrados seguem legíveis, sem downtime). Documentos cujo **binário já foi perdido no disco** são **ignorados automaticamente** (contados como *"sem arquivo no disco (ignorados)"*, não como erro) — o comando termina com sucesso. Só um erro **inesperado** (ex.: S3 fora do ar) faz a execução falhar. Para conferir/limpar inconsistências entre banco e MinIO depois:

```bash
sudo docker compose exec backend-core python manage.py reconcile_storage                       # relatório (dry-run)
sudo docker compose exec backend-core python manage.py reconcile_storage --direction storage-to-db --delete-orphans
```

---

## 7. Solução de problemas rápida

| Sintoma | Causa provável | Ação |
|---|---|---|
| `port is already allocated` / `bind ... address already in use` (9000, **9002 ou 9003**) | Porta do host ocupada por outro MinIO (`milvus-minio`) **ou por outro usuário/forward em servidor compartilhado** — inclusive processos em `127.0.0.1` (ex.: túnel SSH `-L`/PORTS do VS Code de outra pessoa). O Docker binda `0.0.0.0:PORTA` e colide com qualquer bind da mesma porta, mesmo em loopback. | As portas do host são configuráveis: no `.env`, ajuste `MINIO_API_PORT`/`MINIO_CONSOLE_PORT` para portas livres (ex.: `19002`/`19003`) e suba de novo. Descubra o que está livre com `ss -ltn \| grep -E ':900[0-9]\|:1900[0-9]'`. O interno (9000/9001) e a rede da app **não** mudam. Lembre de encaminhar as **novas** portas no VS Code/SSH. |
| Serviços presos em *waiting for minio to be healthy* | Healthcheck do `minio` (`mc ready local`) | Pré-existente; pode exigir ajuste do healthcheck do serviço `minio`. |
| URIs no banco continuam `local://` | Backend `s3` não ativo | Cheque `DOCUPARSE_STORAGE_BACKEND=s3` nos serviços. |
| Erro de credencial/endpoint ao servir/enviar arquivo | `S3_*`/`AWS_*` incorretos ou bucket inexistente | Verifique env e se `minio-setup` criou o bucket (`mc ls local/docuparse`). |

> Fora do escopo desta feature: o bug de rede na sincronização ingestão→core ("documento não aparece na listagem") é um problema **separado** e não é resolvido por esta mudança.
