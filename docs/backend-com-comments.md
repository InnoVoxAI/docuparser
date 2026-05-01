# Analise do backend-com contra as especificacoes

## Resumo executivo

O diretorio `docuparse-project/backend-com` atende parcialmente as especificacoes. Ele contem componentes funcionais importantes para captura de email via IMAP, webhook de WhatsApp via Twilio, envio outbound de WhatsApp, utilitario de webhook HTTP, fila com debounce e uma aplicacao FastAPI. Porem, o codigo atual ainda se comporta mais como uma biblioteca reutilizavel chamada `atoms` do que como o microservico `backend-com` especificado para o DocuParse.

Para atender ao PRD, o `backend-com` precisa ser promovido a um servico de captura de documentos, com contratos canonicos, armazenamento de arquivos, publicacao de eventos `document.received`, endpoints versionados por canal, multi-tenant, testes especificos de captura e Docker de runtime integrado ao `docker-compose` principal.

## O que ja atende ou pode ser reaproveitado

1. **Arquitetura FastAPI existente**
   - Existe app FastAPI em `src/atoms/fastapi_app.py`.
   - Ja agrega rotas de email e WhatsApp.
   - Pode ser reaproveitado como base do microservico `backend-com`, mas precisa ser renomeado/configurado para DocuParse.

2. **Captura de email por IMAP**
   - `src/atoms/email_reader/service/email_reader.py` le emails nao lidos, extrai metadados, corpo, anexos e imagens inline.
   - `src/atoms/email_reader/api/v1/fastapi.py` expoe `/fetch_unread`.
   - O daemon consegue varrer a caixa periodicamente e enviar cada anexo para um webhook externo.
   - Isso cobre parcialmente o requisito de email, mas ainda nao cobre webhook canonico nem evento `document.received`.

3. **Captura de WhatsApp via webhook Twilio**
   - `src/atoms/whatsapp/twilio/service/webhook.py` expoe `/webhook/twilio`.
   - Valida remetente, suporta assinatura Twilio opcional, aplica rate limit simples e repassa payload para webhook externo.
   - O desenho e reaproveitavel para `POST /api/v1/whatsapp/webhook`.

4. **Fila/debounce reaproveitavel**
   - `src/atoms/debounce/debounced_queue.py` implementa backends em memoria, Postgres e Celery/Redis.
   - Isso e util para debounce de mensagens, mas nao substitui o event bus do pipeline de documentos.

5. **Docker de desenvolvimento**
   - Existe `.devcontainer/docker-compose.yml` com workspace, Postgres e Redis.
   - Isso ajuda no desenvolvimento, mas nao disponibiliza o `backend-com` no `docuparse-project/docker-compose.yml`.

## Lacunas em relacao as especificacoes

### 1. O projeto ainda nao e um microservico DocuParse completo

O pacote se chama `atoms`, o app se apresenta como "Atoms API" e as rotas sao genericas. A especificacao pede um `backend-com` autonomo para captura de Email, WhatsApp e upload manual.

Alteracoes necessarias:

- Definir uma camada de aplicacao `backend_com` ou `docuparse_backend_com` em cima dos componentes `atoms`.
- Manter `atoms` como biblioteca interna, se desejado, mas criar endpoints e schemas do dominio DocuParse.
- Alterar titulo, descricao, tags, configuracoes e logs para `backend-com`.
- Criar estrutura sugerida:

```text
backend-com/
  src/
    backend_com/
      api/v1/email.py
      api/v1/whatsapp.py
      api/v1/documents.py
      domain/events.py
      domain/documents.py
      services/capture_email.py
      services/capture_whatsapp.py
      services/manual_upload.py
      services/storage.py
      services/event_publisher.py
      settings.py
```

### 2. Rotas nao seguem os contratos especificados

Rotas atuais relevantes:

- `POST /fetch_unread`
- `POST /webhook/twilio`
- `POST /send_message`
- `POST /send_typing`
- `POST /echo_data`

Rotas esperadas pelo PRD:

- `POST /api/v1/email/webhook`
- `POST /api/v1/email/messages`
- `GET /api/v1/email/accounts`
- `POST /api/v1/email/accounts`
- `POST /api/v1/whatsapp/webhook`
- `GET /api/v1/whatsapp/numbers`
- `POST /api/v1/whatsapp/numbers`
- `POST /api/v1/whatsapp/messages/test`
- `POST /api/v1/documents/manual`

Alteracoes necessarias:

- Manter adaptadores legados como endpoints internos, se forem uteis.
- Criar endpoints versionados `/api/v1/...`.
- Separar claramente API de email e API de WhatsApp.
- Padronizar respostas com `document_id`, `status`, `accepted_documents`, `ignored_attachments` e `correlation_id`.

### 3. Email atende apenas polling IMAP; falta webhook de provedor

A especificacao pede captura de email por API/webhook quando disponivel, com IMAP como adaptador secundario. Hoje o suporte principal e IMAP via `/fetch_unread` ou daemon.

Alteracoes necessarias:

- Implementar `POST /api/v1/email/webhook` para provedores como SendGrid, Mailgun, Gmail Pub/Sub ou adaptador custom.
- Normalizar payloads de provedores para um modelo interno `InboundEmail`.
- Manter IMAP em `POST /api/v1/email/messages` ou worker agendado como fallback.
- Garantir que cada anexo aceito gere um `document.received`.
- Validar assinatura/token do provedor de email quando aplicavel.

### 4. WhatsApp recebe webhook, mas nao captura documento para o pipeline

O webhook Twilio atual extrai somente a primeira midia (`MediaUrl0`, `MediaContentType0`) e repassa o payload para um webhook configurado. Ele nao baixa a midia, nao armazena arquivo, nao valida tipo/tamanho, nao cria documento e nao publica `document.received`.

Alteracoes necessarias:

- Processar todas as midias `MediaUrl0..N`, nao apenas a primeira.
- Baixar midias do Twilio com autenticacao correta.
- Aceitar somente MIME types suportados pelo pipeline, por exemplo PDF e imagens.
- Armazenar arquivo em object storage ou volume persistente.
- Criar `document_id` por midia aceita.
- Publicar `document.received` com `source="whatsapp"`.
- Retornar status de recebimento imediatamente ao Twilio, sem depender do webhook externo.

### 5. Upload manual nao existe no backend-com

O PRD exige upload por tela de usuario com metadados. O `backend-com` atual nao possui endpoint de upload manual.

Alteracoes necessarias:

- Criar `POST /api/v1/documents/manual` com `multipart/form-data`.
- Campos minimos:
  - `file`
  - `tenant_id`
  - `operator_id`
  - `scan_date`
  - `expected_document_type`
  - `batch_id` opcional
  - `condominio` ou referencia equivalente quando aplicavel
  - `notes` opcional
- Validar extensao, MIME type, tamanho, duplicidade e legibilidade basica.
- Armazenar arquivo e publicar `document.received` com `source="manual"`.

### 6. Nao ha publicacao real no event bus do pipeline

O codigo atual usa `send_to_webhook.py` para repassar payloads HTTP. Isso nao atende a comunicacao por filas/eventos definida no PRD.

Alteracoes necessarias:

- Criar `EventPublisher` com implementacao inicial para Redis/RabbitMQ/Celery ou outra fila escolhida no projeto.
- Publicar evento canonico:

```json
{
  "event": "document.received",
  "version": "v1",
  "document_id": "uuid",
  "tenant_id": "uuid",
  "source": "email|whatsapp|manual|watched_folder",
  "file_uri": "s3://bucket/file.pdf",
  "metadata": {},
  "correlation_id": "uuid"
}
```

- Remover dependencia operacional de `imap_reader_webhook_url` e `twilio_webhook_url` como mecanismo principal do pipeline.
- Manter callbacks HTTP apenas como integracao externa opcional.

### 7. Falta persistencia de documento e armazenamento de arquivo

Email e WhatsApp hoje carregam conteudo em memoria ou repassam base64/URL para webhook. A especificacao pede que o `backend-com` armazene o documento original e publique o `file_uri`.

Alteracoes necessarias:

- Implementar `StorageService` para salvar documentos em S3/MinIO ou volume local configuravel.
- Calcular checksum para idempotencia e deduplicacao.
- Persistir tabela de captura, por exemplo:
  - `captured_documents`
  - `capture_sources`
  - `capture_attempts`
  - `email_accounts`
  - `whatsapp_numbers`
- Registrar `document_id`, `tenant_id`, `source`, `file_uri`, `checksum`, `mime_type`, `size_bytes`, `status`, `created_at`.

### 8. Multi-tenant ainda nao esta implementado

As configuracoes atuais sao globais por `.env`. O PRD pede configuracoes isoladas por tenant para email, numeros WhatsApp, webhooks, chaves e canais.

Alteracoes necessarias:

- Modelar tenants e configuracoes por tenant.
- Resolver `tenant_id` por email destino, numero WhatsApp destino, subdominio ou token do webhook.
- Nao usar uma unica conta IMAP global para todos os tenants.
- Nao usar um unico `twilio_settings.webhook_url` global como destino principal.

### 9. Segurança precisa de ajustes imediatos

Foi encontrado segredo real ou com aparencia de segredo em `.env` e `.env.example`:

- `imap_reader_password=...`

Mesmo que seja uma senha de teste, nao deve ficar versionada. Alem disso, o webhook Twilio vem com `validate_twilio_signature=False` por padrao.

Alteracoes necessarias:

- Remover segredos de `.env.example`.
- Rotacionar a senha exposta se ela for valida.
- Garantir que `.env` nao seja versionado.
- Exigir `validate_twilio_signature=True` em ambientes nao locais.
- Proteger endpoints administrativos por token ou autenticacao de servico.
- Restringir CORS; hoje `allow_origins=["*"]`.
- Evitar recebimento de credenciais via form em endpoints publicos como `/fetch_unread`.

### 10. Docker e composicao nao atendem ao runtime do sistema

Existe Docker apenas no `.devcontainer`. O `docuparse-project/docker-compose.yml` principal nao inclui `backend-com`, Redis, Postgres dedicado, fila/event bus nem storage.

Alteracoes necessarias:

- Criar `docuparse-project/backend-com/Dockerfile` de runtime.
- Adicionar `backend-com` ao `docuparse-project/docker-compose.yml`.
- Adicionar variaveis de ambiente especificas do servico.
- Adicionar dependencia de fila/event bus e storage.
- Expor porta propria, por exemplo `8010`, evitando conflito com `backend-core` em `8000`.
- Ajustar `prestart_dev.sh`, que hoje sobe o `backend-com` em `8000`, conflitando conceitualmente com o `backend-core`.

### 11. Observabilidade e logs nao atendem ao PRD

Existe `structlog`, mas a configuracao atual em `fastapi_app.py` usa `json_logs=False` e `console_logs=False`, o que pode descartar logs estruturados. Tambem faltam `correlation_id`, `tenant_id`, `document_id`, metricas e traces.

Alteracoes necessarias:

- Padronizar logs JSON em runtime.
- Incluir `service="backend-com"`, `correlation_id`, `tenant_id`, `document_id`, `source`.
- Adicionar health check e readiness:
  - `GET /health`
  - `GET /ready`
- Instrumentar OpenTelemetry.
- Emitir metricas:
  - documentos capturados por canal
  - anexos rejeitados
  - falhas de webhook
  - latencia de download de midia
  - eventos publicados

### 12. Testes atuais nao cobrem o backend-com especificado

Ha testes apenas para `DebouncedQueue` em `src/atoms/debounce/pytest.py`. Nao ha testes de contrato para email, WhatsApp, upload manual, eventos ou Docker.

Alteracoes necessarias:

- Renomear/mover `src/atoms/debounce/pytest.py` para um caminho padrao, por exemplo `tests/test_debounced_queue.py`.
- Criar testes unitarios:
  - parser IMAP
  - normalizacao de email webhook
  - webhook Twilio com assinatura valida/invalida
  - download de midia
  - validacao de arquivo
  - publicacao de `document.received`
- Criar testes de integracao:
  - email com dois anexos gera dois eventos
  - WhatsApp com N midias gera N documentos
  - upload manual gera um documento com metadados
  - evento duplicado nao duplica documento
  - fila indisponivel gera erro/retry controlado

## Proposta de plano de alteracao

### Prioridade 0 - Seguranca

- Remover segredos de `.env.example`.
- Rotacionar senha exposta, se valida.
- Garantir `.env` fora do versionamento.
- Ativar validacao de assinatura Twilio por ambiente.

### Prioridade 1 - Transformar em microservico de captura

- Criar camada `backend_com` com FastAPI propria.
- Implementar rotas `/api/v1/...` exigidas.
- Manter codigo `atoms` como adaptadores internos.
- Adicionar health/readiness.

### Prioridade 2 - Evento canonico e storage

- Implementar `StorageService`.
- Implementar `EventPublisher`.
- Publicar `document.received` para email, WhatsApp e upload manual.
- Persistir captura e idempotencia.

### Prioridade 3 - Canais

- Email: adicionar webhook de provedor e manter IMAP como fallback.
- WhatsApp: baixar todas as midias, validar arquivos e publicar eventos.
- Manual: criar endpoint multipart com metadados.

### Prioridade 4 - Runtime e testes

- Criar Dockerfile de runtime.
- Adicionar `backend-com` ao compose principal.
- Adicionar testes unitarios, contrato e integracao.
- Instrumentar logs JSON, metricas e traces.

## Veredito

O `backend-com` atual e uma boa base tecnica para reaproveitar captura IMAP, webhook Twilio e algumas utilidades de fila/logging, mas ainda nao atende as especificacoes fechadas como microservico de captura do DocuParse. As principais faltas sao: endpoints canonicos, upload manual, armazenamento, publicacao em fila de `document.received`, multi-tenant, runtime Docker no compose principal e testes de contrato/integracao por canal.
