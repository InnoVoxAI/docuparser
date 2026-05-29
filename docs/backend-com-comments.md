# Analise do backend-com contra as especificacoes

## Resumo executivo

O diretorio `docuparse-project/backend-com` evoluiu de uma biblioteca de utilitarios `atoms` para um microservico de captura de documentos funcional. O servico se apresenta como `"DocuParse Backend COM"`, expoe oito endpoints versionados em `/api/v1/...`, cobre os tres canais de captura (email, WhatsApp e upload manual), publica `document.received` em event bus configuravel (Redis ou JSONL local), persiste arquivos via `docuparse_storage`, e tem Docker de runtime integrado ao `docker-compose` principal. A suite de testes cobre os fluxos criticos com 21 testes.

As lacunas remanescentes sao pontuais: os endpoints de readiness nao verificam dependencias externas (Redis, MinIO, backend-core); a validacao de assinatura dos webhooks e por comparacao simples de string em vez de HMAC; e o Dockerfile de producao nao lista as dependencias opcionais necessarias para email e WhatsApp.

## O que ja atende

### 1. Microservico FastAPI dedicado ao DocuParse

`src/backend_com/api/app.py` define o servico `"DocuParse Backend COM"` com lifespan propria. A camada `atoms` permanece como biblioteca interna de utilitarios; o dominio do servico vive em `src/backend_com/`.

```text
backend_com/
  api/app.py               # FastAPI com 8 endpoints
  services/
    document_ingest.py     # storage + publicacao de eventos
    email_capture.py
    imap_polling.py
    manual_upload.py
    whatsapp_capture.py
    twilio_polling.py
  config.py
  imap_poll.py             # CLI para poll unico
```

### 2. Todos os endpoints versionados implementados

| Metodo | Path | Funcao |
|--------|------|--------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/ready` | Readiness probe |
| `POST` | `/api/v1/documents/manual` | Upload manual de arquivo |
| `POST` | `/api/v1/email/webhook` | Webhook de email (SendGrid, Mailgun, etc.) |
| `POST` | `/api/v1/email/messages` | Ingestao interna de emails IMAP |
| `POST` | `/api/v1/email/poll` | Dispara poll IMAP uma vez |
| `POST` | `/api/v1/whatsapp/webhook` | Webhook Twilio de WhatsApp |
| `POST` | `/api/v1/whatsapp/poll` | Dispara poll Twilio REST API uma vez |

Todos os endpoints de ingestao retornam resposta padronizada:

```json
{
  "accepted_count": 2,
  "documents": [
    {
      "document_id": "uuid",
      "event_id": "uuid",
      "file_uri": "local://...",
      "size_bytes": 123456,
      "sha256": "hex",
      "event_type": "document.received",
      "channel": "email|whatsapp|manual",
      "core_sync_status": "synced:200|failed|disabled"
    }
  ],
  "duplicate_count": 0
}
```

### 3. Publicacao do evento document.received

`services/document_ingest.py` publica o evento canonico via `event_bus_from_env()` (abstrai Redis ou JSONL local via `DOCUPARSE_EVENT_BUS`):

```json
{
  "event_type": "document.received",
  "tenant_id": "uuid",
  "document_id": "uuid",
  "correlation_id": "uuid",
  "source": "backend-com",
  "data": {
    "channel": "manual|email|whatsapp",
    "received_at": "ISO8601",
    "sender": "email ou telefone",
    "file": {
      "uri": "local://...",
      "content_type": "application/pdf",
      "filename": "nota.pdf",
      "size_bytes": 123456,
      "sha256": "hex"
    },
    "metadata": {
      "provider": "webhook|imap|twilio",
      "message_id": "...",
      "subject": "...",
      "metadata_channel": { ... }
    }
  }
}
```

Apos publicar no event bus, o servico tambem sincroniza via HTTP para `BACKEND_CORE_DOCUMENT_RECEIVED_URL`. Falhas de sincronizacao com o core sao registradas em log sem derrubar a ingestao.

### 4. Storage de arquivos implementado

`docuparse_storage.LocalStorage` persiste cada arquivo com chave `document_original_key(tenant_id, document_id)`. O objeto retornado carrega `uri`, `size_bytes` e `sha256`. O diretorio e configuravel via `DOCUPARSE_LOCAL_STORAGE_DIR`.

### 5. Captura de email: webhook e IMAP

- `POST /api/v1/email/webhook`: aceita multiplos anexos via multipart, valida assinatura por header `x-docuparse-signature`, processa cada anexo separadamente.
- `POST /api/v1/email/poll`: busca configuracoes IMAP por tenant no backend-core (`BACKEND_CORE_EMAIL_SETTINGS_URL`), conecta via `imaplib.IMAP4_SSL`, filtra remetentes bloqueados e MIME types invalidos, respeita limite de tamanho por tenant, marca como lida opcionalmente (`DOCUPARSE_IMAP_MARK_AS_READ`).

### 6. WhatsApp: webhook e polling Twilio completos

- `POST /api/v1/whatsapp/webhook`: processa todas as midias `MediaUrl0..N` (nao apenas a primeira), extrai conteudo base64 inline quando presente, baixa midias do Twilio com autenticacao `Basic(account_sid:auth_token)` quando necessario, filtra por MIME type.
- `POST /api/v1/whatsapp/poll`: consulta a Twilio Messages API, baixa cada midia, deduplica por SHA256 na sessao, delega ao core para deduplicacao persistente via retorno 409.

### 7. Upload manual com validacao completa

`POST /api/v1/documents/manual`:
- Aceita `multipart/form-data` com `file`, `tenant_id`, `sender` e `metadata_json`.
- Valida Bearer token quando `DOCUPARSE_INTERNAL_SERVICE_TOKEN` configurado.
- Rejeita arquivos acima de `DOCUPARSE_MAX_UPLOAD_BYTES` (padrao 20 MB).
- Rejeita MIME types fora da lista permitida (PDF, JPEG, PNG, TIFF, WebP).
- Retorna 409 Conflict para documentos duplicados.

### 8. Multi-tenant implementado

`tenant_id` e resolvido por campo de formulario em todos os endpoints. Cada documento e armazenado sob prefixo do tenant. O poll IMAP busca configuracoes especificas por tenant (host, usuario, MIME types aceitos, remetentes bloqueados, tamanho maximo) diretamente do backend-core.

### 9. Seguranca ajustada

- Bearer token validado com `hmac.compare_digest()` para prevenir timing attacks nos endpoints internos (manual, poll).
- Credenciais IMAP nao sao logadas; apenas comprimento e registrado no startup.
- CORS restrito a origens configuradas via `CORS_ALLOWED_ORIGINS`.
- Limite de tamanho de upload por arquivo e por tenant.
- Filtro de MIME types em todos os canais.

### 10. Docker de runtime e integracao no compose

`Dockerfile` de producao baseado em `python:3.13-slim`, porta `8070`. O servico esta incluido no `docker-compose.yml` principal com:
- Volumes montados para storage, events, contratos e shared.
- Variaveis de ambiente para Redis, MinIO, backend-core.
- Health check apontando para `GET /health`.
- Dependencias de Redis e MinIO via `depends_on`.

### 11. Observabilidade com correlation_id

`services/document_ingest.py` usa `log_event()` de `docuparse_observability` com campos:
- `tenant_id`, `document_id`, `correlation_id`, `event_type`, `channel`, `file_uri`, `core_sync_status`.

O `correlation_id` e gerado por documento e propagado para o evento e os logs.

### 12. Suite de testes abrangente

```text
tests/
  conftest.py
  test_backend_com_app.py    # 21 testes
```

Cobertura:
- health e ready.
- upload manual: storage, evento publicado, validacao de MIME, validacao de token, falha graceful do core.
- email webhook: zero anexos, multiplos anexos, MIME invalido, assinatura.
- IMAP poll: ingestao com mock client, filtragem de remetente bloqueado e MIME invalido, exigencia de senha.
- WhatsApp webhook: zero midias, multiplas midias inline (base64), MIME invalido, assinatura.

## Lacunas remanescentes

### 1. Endpoints /health e /ready nao verificam dependencias

Ambos retornam 200 incondicionalmente. Um servico sem conexao com Redis, sem acesso ao MinIO ou com backend-core indisponivel reporta `ready` da mesma forma que um servico operacional.

Alteracoes necessarias:

- Adicionar verificacao real em `GET /ready`:
  - Conectividade com Redis (ou event bus configurado).
  - Acesso ao diretorio de storage (escrita).
  - Opcional: `HEAD` no `BACKEND_CORE_DOCUMENT_RECEIVED_URL`.
- Retornar 503 com detalhe da dependencia que falhou.

### 2. Validacao de assinatura dos webhooks e por comparacao simples

Os endpoints `POST /api/v1/email/webhook` e `POST /api/v1/whatsapp/webhook` comparam o header `x-docuparse-signature` com o token configurado por igualdade direta de string. Isso e vulneravel a timing attacks.

Alteracoes necessarias:

- Substituir comparacao direta por `hmac.compare_digest()`, alinhando com a validacao ja feita nos endpoints internos.
- Documentar o formato esperado do header (ex: HMAC-SHA256 do corpo ou token Bearer simples).

### 3. Dependencias opcionais ausentes no Dockerfile de producao

O `Dockerfile` instala apenas as dependencias base (fastapi, uvicorn, pydantic, structlog, redis). As dependencias necessarias para email e WhatsApp (`imap-tools`, `httpx`, `twilio`) nao estao listadas, o que pode causar falha silenciosa no runtime.

Alteracoes necessarias:

- Incluir as dependencias opcionais necessarias no `Dockerfile` ou criar perfis de build:

```text
requirements-base.txt
requirements-email.txt
requirements-whatsapp.txt
```

- Garantir que a imagem de producao contenha tudo necessario para os canais ativos.

## Proposta de plano de alteracao

### Prioridade 1 - Readiness com verificacao real de dependencias

- Implementar checagem de Redis e storage em `GET /ready`.
- Retornar 503 com diagnose quando alguma dependencia estiver indisponivel.

### Prioridade 2 - Proteger assinaturas dos webhooks com timing-safe comparison

- Substituir comparacao direta por `hmac.compare_digest()` em email webhook e WhatsApp webhook.

### Prioridade 3 - Corrigir dependencias no Dockerfile

- Mapear quais dependencias sao necessarias por canal ativo.
- Incluir ou parametrizar no Dockerfile de producao.

## Veredito

O `backend-com` esta operacional como microservico de captura. Os tres canais (manual, email e WhatsApp) estao implementados, o evento `document.received` e publicado com contrato canonico, storage e multi-tenant funcionam, o Docker esta integrado ao compose principal e os testes cobrem os fluxos criticos. As lacunas remanescentes sao objetivas: readiness sem verificacao real de dependencias, validacao de assinatura de webhook sem timing-safe comparison, e dependencias opcionais ausentes no Dockerfile.
