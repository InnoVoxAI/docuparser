# Plano de acao de implementacao - DocuParse

## Objetivo

Implementar o sistema completo conforme as especificacoes fechadas em `docs/specs/ingest_docs_prd.md`, usando os comentarios de diagnostico em:

- `docs/backend-com-comments.md`
- `docs/backend-ocr-comments.md`

Fluxo alvo:

```text
captura -> document.received -> OCR -> ocr.completed -> Layout -> layout.classified -> LangExtract -> extraction.completed -> validacao -> erp.integration.requested -> backend-conect -> erp.sent
```

## Como manter este plano atualizado

Este arquivo deve ser atualizado ao longo do projeto. Cada task possui status e criterio de aceite. Ao concluir ou bloquear uma task, atualizar:

- `Status`
- `Atualizado em`
- `Evidencia`
- `Pendencias`

Legenda:

| Status | Uso |
|--------|-----|
| `TODO` | Nao iniciado |
| `DOING` | Em execucao |
| `BLOCKED` | Bloqueado por decisao, credencial, dependencia ou bug externo |
| `REVIEW` | Implementado e aguardando revisao |
| `DONE` | Concluido com testes/criterios atendidos |

Regra de qualidade:

- Nenhuma fase deve ser considerada pronta sem testes unitarios e de contrato.
- Nenhum modulo deve ser conectado ao pipeline antes de passar isoladamente.
- Testes de carga devem usar mocks/sandboxes para APIs externas, exceto quando aprovado explicitamente.

## Decisoes tecnicas assumidas inicialmente

Estas decisoes podem ser revisadas, mas devem estar explicitas:

| Tema | Decisao inicial |
|------|-----------------|
| Backend core | Refeito em Django + DRF, mantendo papel de orquestrador e validacao humana |
| Frontend | Refeito em React/Vite ou migrado para Next.js se autenticacao/rotas server-side forem priorizadas |
| Event bus | RabbitMQ ou Redis Streams; escolher antes da Fase 1 |
| Storage | S3/MinIO em desenvolvimento, S3 compativel em producao |
| OCR inicial | OpenRouter para imagens/PDFs escaneados; Docling para PDFs com texto |
| LangExtract | Microservico separado, sem misturar com OCR |
| ERP inicial | `backend-conect` com conector Superlogica e mock ERP |
| Testes de carga | Locust ou k6, com cenarios simulados por canal |

## Dados e credenciais necessarios

Preencher antes das fases que dependem de integracoes reais.

### Obrigatorios para ambiente de desenvolvimento integrado

| Item | Necessario para | Valor a fornecer |
|------|-----------------|------------------|
| `OPENROUTER_API_KEY` | OCR via OpenRouter | `PENDENTE` |
| `OPENROUTER_MODEL` | OCR via OpenRouter | `PENDENTE` |
| URL publica para webhooks locais | WhatsApp/email em testes reais | `PENDENTE` |
| Email de teste para recebimento | Captura de email | `PENDENTE` |
| Credenciais IMAP ou provedor webhook | Captura de email | `PENDENTE` |
| Provedor de email webhook | SendGrid/Mailgun/Gmail PubSub/custom | `PENDENTE` |
| Numero WhatsApp de teste | Captura WhatsApp | `PENDENTE` |
| Twilio Account SID | WhatsApp Twilio | `PENDENTE` |
| Twilio Auth Token | Validacao webhook Twilio | `PENDENTE` |
| Twilio API Key SID | Envio/teste WhatsApp | `PENDENTE` |
| Twilio API Key Secret | Envio/teste WhatsApp | `PENDENTE` |
| Twilio From Number | Numero WhatsApp remetente | `PENDENTE` |
| Tenant inicial | Multi-tenant | `PENDENTE` |
| Usuario operador inicial | Validacao humana | `PENDENTE` |
| Usuario supervisor inicial | Configuracoes | `PENDENTE` |
| Arquivos de teste reais | OCR/layout/LangExtract | `PENDENTE` |
| Superlogica sandbox base URL | backend-conect | `PENDENTE` |
| Superlogica credenciais sandbox | backend-conect | `PENDENTE` |

### Parametros para testes de carga

| Item | Valor default sugerido | Valor real |
|------|------------------------|------------|
| Emails/hora | 300 | `PENDENTE` |
| WhatsApps/hora | 300 | `PENDENTE` |
| Uploads manuais/hora | 120 | `PENDENTE` |
| Tamanho medio do arquivo | 2 MB | `PENDENTE` |
| Tamanho maximo do arquivo | 20 MB | `PENDENTE` |
| P95 maximo para aceite de captura | 2 s | `PENDENTE` |
| P95 maximo para OCR | 90 s | `PENDENTE` |
| Backlog maximo aceitavel na fila | 100 jobs | `PENDENTE` |
| Taxa maxima de erro aceitavel | 1% | `PENDENTE` |

## Marcos do projeto

| Marco | Resultado esperado | Status |
|-------|--------------------|--------|
| M0 | Contratos, compose base e dados de ambiente definidos | TODO |
| M1 | `backend-com` captura documentos e publica `document.received` | TODO |
| M2 | `backend-ocr` consome evento e publica `ocr.completed` | TODO |
| M3 | `layout-service` classifica layout e publica `layout.classified` | TODO |
| M4 | `langextract-service` extrai dados e publica `extraction.completed` | TODO |
| M5 | `backend-core` persiste estados e suporta validacao humana | TODO |
| M6 | `backend-conect` envia payload aprovado para ERP/mock ERP | TODO |
| M7 | Frontend novo suporta upload, inbox, validacao e configuracoes | TODO |
| M8 | Observabilidade, seguranca e testes de carga integrados | TODO |
| M9 | E2E por email, WhatsApp e upload manual ate ERP | TODO |

## Fase 0 - Fundacao e contratos

### T-0001 - Escolher event bus e storage

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: todos
- Dependencias: nenhuma
- Entrega:
  - Decisao documentada: RabbitMQ/Redis Streams/Celery para eventos.
  - Decisao documentada: MinIO/S3/local storage.
  - `docker-compose.yml` planejado com event bus, storage e Postgres.
- Testes:
  - Subir compose minimo com health checks.
  - Publicar e consumir evento fake.
- Criterio de aceite:
  - Um script local publica `document.received.fake` e outro consome.

### T-0002 - Definir contratos canonicos de eventos

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: todos
- Dependencias: T-0001
- Entrega:
  - Schemas versionados para:
    - `document.received`
    - `ocr.completed`
    - `ocr.failed`
    - `layout.classified`
    - `extraction.completed`
    - `erp.integration.requested`
    - `erp.sent`
    - `erp.failed`
  - Pasta sugerida: `docuparse-project/contracts/events/`.
- Testes:
  - Validacao Pydantic/JSON Schema dos exemplos.
  - Teste de compatibilidade de versao `v1`.
- Criterio de aceite:
  - Cada modulo consegue importar/validar os contratos sem dependencias circulares.

### T-0003 - Definir modelo de storage e URIs

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-com, backend-ocr, backend-core, frontend
- Dependencias: T-0001
- Entrega:
  - Convencao de paths:
    - `documents/{tenant_id}/{document_id}/original`
    - `documents/{tenant_id}/{document_id}/ocr/raw_text.json`
    - `documents/{tenant_id}/{document_id}/artifacts/...`
  - Servico comum de storage ou biblioteca pequena.
- Testes:
  - Upload/download/delete em MinIO/local.
  - Arquivo grande simulado.
- Criterio de aceite:
  - `file_uri` e `raw_text_uri` sao resolvidos por todos os modulos que precisam.

### T-0004 - Atualizar docker-compose base

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: infra
- Dependencias: T-0001
- Entrega:
  - `backend-com`, `backend-ocr`, `backend-core`, `layout-service`, `langextract-service`, `backend-conect`, `frontend`.
  - Postgres, event bus, storage, observabilidade basica.
  - Portas sem conflito.
- Testes:
  - `docker compose up` sobe todos os health checks.
- Criterio de aceite:
  - Todos os servicos respondem `/health`.

## Fase 1 - Backend COM

### T-0101 - Transformar `backend-com` em microservico DocuParse

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-com
- Dependencias: T-0002, T-0003
- Entrega:
  - Criar camada `backend_com` sobre `atoms`.
  - App FastAPI com titulo/health/readiness de `backend-com`.
  - Rotas `/api/v1/...`.
- Testes:
  - Unitarios de app startup.
  - Contract tests das respostas basicas.
- Criterio de aceite:
  - `GET /health` e `GET /ready` passam.

### T-0102 - Implementar upload manual

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-com, frontend
- Dependencias: T-0101, T-0003
- Entrega:
  - `POST /api/v1/documents/manual`.
  - Validacao de arquivo e metadados.
  - Storage do documento original.
  - Publicacao `document.received`.
- Testes:
  - Unitario de validacao de metadados.
  - Integracao com storage e event bus.
  - Carga simulada: 120 uploads/hora, arquivos 2 MB.
- Criterio de aceite:
  - Upload gera exatamente um documento e um evento.

### T-0103 - Implementar captura de email

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-com
- Dependencias: T-0101, T-0002, T-0003
- Entrega:
  - `POST /api/v1/email/webhook`.
  - `POST /api/v1/email/messages` para IMAP/polling.
  - Contas por tenant.
  - Cada anexo aceito vira um `document.received`.
- Testes:
  - Email com 0, 1 e N anexos.
  - Anexo invalido rejeitado.
  - Assinatura/token de provedor.
  - Carga simulada: 300 emails/hora, media 2 anexos/email.
- Criterio de aceite:
  - Email com N anexos gera N documentos aceitos e N eventos.

### T-0104 - Implementar captura de WhatsApp

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-com
- Dependencias: T-0101, T-0002, T-0003
- Entrega:
  - `POST /api/v1/whatsapp/webhook`.
  - Validacao Twilio.
  - Download de todas as midias.
  - Storage do arquivo.
  - Publicacao `document.received`.
- Testes:
  - Webhook com assinatura valida/invalida.
  - 0, 1 e N midias.
  - PDF, imagem e MIME invalido.
  - Carga simulada: 300 mensagens/hora.
- Criterio de aceite:
  - Mensagem com N midias validas gera N documentos e N eventos.

## Fase 2 - Backend OCR

### T-0201 - Corrigir bugs do fluxo atual

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-ocr
- Dependencias: nenhuma
- Entrega:
  - Corrigir chamada de `classify_document`.
  - Corrigir chamada de `merge_fallback_result`.
  - Corrigir `ocr_result` indefinido.
  - Corrigir `debug`/`_debug`.
  - Preservar HTTP 400.
- Testes:
  - Unitarios para cada bug.
  - `/api/v1/process` com fixture PDF/imagem.
- Criterio de aceite:
  - Endpoint processa fixture sem cair em fallback por bug de assinatura.

### T-0202 - Definir perfil OpenRouter + Docling

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-ocr
- Dependencias: T-0201
- Entrega:
  - `digital_pdf -> docling`.
  - `scanned_image -> openrouter`.
  - `handwritten_complex -> openrouter`.
  - Registry lazy real.
  - Engines legadas opcionais.
- Testes:
  - Resolver por content type.
  - Readiness falha sem `OPENROUTER_API_KEY` quando OpenRouter habilitado.
- Criterio de aceite:
  - `GET /api/v1/engines` mostra apenas engines habilitadas e status real.

### T-0203 - Separar OCR de extracao semantica

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-ocr, langextract-service
- Dependencias: T-0201
- Entrega:
  - Caminho principal retorna texto bruto, content type, document type e metadados.
  - `FieldExtractor` sai do fluxo principal.
  - Modo legado opcional, se necessario.
- Testes:
  - Resposta OCR sem campos estruturados.
  - Compatibilidade com contrato `ocr.completed`.
- Criterio de aceite:
  - `backend-ocr` nao publica campos financeiros extraidos.

### T-0204 - Consumir `document.received` e publicar `ocr.completed`

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-ocr
- Dependencias: T-0002, T-0003, T-0202, T-0203
- Entrega:
  - Worker/consumer do event bus.
  - Download do `file_uri`.
  - Storage de `raw_text.json`.
  - Publicacao `ocr.completed` ou `ocr.failed`.
- Testes:
  - Contrato entrada/saida.
  - Integracao com storage e event bus.
  - Carga simulada: 100 documentos/hora com OpenRouter mock.
- Criterio de aceite:
  - Evento `document.received` vira `ocr.completed` com `raw_text_uri`.

## Fase 3 - Layout Service

### T-0301 - Criar microservico `layout-service`

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: layout-service
- Dependencias: T-0002, T-0003
- Entrega:
  - FastAPI health/readiness.
  - API isolada `POST /api/v1/classify-layout`.
  - Worker para consumir `ocr.completed`.
- Testes:
  - Unitarios de heuristicas.
  - Contrato `layout.classified`.
- Criterio de aceite:
  - Texto bruto + document_type retorna layout e confidence.

### T-0302 - Implementar heuristicas iniciais de layout

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: layout-service
- Dependencias: T-0301
- Entrega:
  - Layouts iniciais:
    - `boleto_caixa`
    - `boleto_bb`
    - `boleto_bradesco`
    - `fatura_energia`
    - `fatura_condominio`
    - `generic`
- Testes:
  - Fixtures por layout.
  - Baixa confianca cai em `generic` ou flag de validacao.
  - Carga simulada: 500 classificacoes/min com textos mockados.
- Criterio de aceite:
  - Cada fixture conhecida classifica corretamente com confidence minimo definido.

## Fase 4 - LangExtract Service

### T-0401 - Criar microservico `langextract-service`

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: langextract-service
- Dependencias: T-0002, T-0003
- Entrega:
  - FastAPI health/readiness.
  - API isolada `POST /api/v1/extract`.
  - Worker para consumir `layout.classified`.
- Testes:
  - Contrato de request/response.
  - Mock LLM para testes deterministas.
- Criterio de aceite:
  - Texto + layout + schema gera `extraction.completed`.

### T-0402 - Implementar schemas versionados de extracao

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: langextract-service, backend-core
- Dependencias: T-0401
- Entrega:
  - Schema versionado por `document_type`, `layout`, `version`.
  - Campos obrigatorios e validadores.
  - Suporte a `boleto` e `fatura` iniciais.
- Testes:
  - Unitarios por schema.
  - Snapshot de payload extraido.
  - Carga simulada: 100 extracoes/hora com LLM mockado.
- Criterio de aceite:
  - `extraction.completed` contem dados, confidence e `requires_human_validation`.

## Fase 5 - Backend Core refeito

### T-0501 - Recriar modelo de dominio e persistencia

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-core
- Dependencias: T-0002
- Entrega:
  - Models/tabelas:
    - Tenant
    - User/Profile
    - Document
    - DocumentEvent
    - ExtractionResult
    - ValidationDecision
    - ERPIntegrationAttempt
    - SchemaConfig
    - LayoutConfig
  - Migracoes PostgreSQL.
- Testes:
  - Unitarios de models.
  - Transicoes de estado.
- Criterio de aceite:
  - Estados do PRD sao persistidos e auditaveis.

### T-0502 - Implementar consumidores de eventos do core

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-core
- Dependencias: T-0501
- Entrega:
  - Consome `document.received`, `extraction.completed`, `erp.sent`, `erp.failed`.
  - Atualiza estados.
  - Cria pendencias de validacao.
- Testes:
  - Contratos de eventos.
  - Idempotencia por `event_id` ou chave equivalente.
  - Carga simulada: 1000 eventos/min com event bus local.
- Criterio de aceite:
  - Reprocessar o mesmo evento nao duplica documento/estado.

### T-0503 - Implementar APIs para frontend

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-core, frontend
- Dependencias: T-0501, T-0502
- Entrega:
  - Inbox de documentos.
  - Detalhe do documento.
  - Validacao/correcao.
  - Aprovar/rejeitar.
  - Configuracoes de schema/layout/canais.
- Testes:
  - API tests com DRF.
  - Autorizacao por perfil.
- Criterio de aceite:
  - Operador consegue validar e aprovar documento via API.

### T-0504 - Publicar `erp.integration.requested`

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-core, backend-conect
- Dependencias: T-0503
- Entrega:
  - Ao aprovar, core publica evento de ERP.
  - Estado muda para `ERP_INTEGRATION_REQUESTED`.
- Testes:
  - Aprovar documento gera um evento.
  - Rejeitar documento nao gera evento ERP.
- Criterio de aceite:
  - `backend-conect` consegue consumir evento aprovado.

## Fase 6 - Backend CONECT

### T-0601 - Criar microservico `backend-conect`

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-conect
- Dependencias: T-0002
- Entrega:
  - FastAPI ou Django/FastAPI.
  - Health/readiness.
  - API isolada para testar normalizacao e envio.
  - Worker para `erp.integration.requested`.
- Testes:
  - Unitarios de contrato canonico.
  - Mock ERP.
- Criterio de aceite:
  - Evento aprovado vira tentativa de integracao persistida.

### T-0602 - Implementar conector Superlogica e mock ERP

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: backend-conect
- Dependencias: T-0601
- Entrega:
  - Normalizador canonico.
  - Conector `superlogica`.
  - Conector `mock`.
  - Idempotencia.
  - Retry e DLQ.
- Testes:
  - Envio com sucesso publica `erp.sent`.
  - Falha retryable agenda retry.
  - Falha final publica `erp.failed`.
  - Carga simulada: 200 integracoes/hora no mock.
- Criterio de aceite:
  - Mesmo documento aprovado duas vezes nao gera duplicidade no ERP.

## Fase 7 - Frontend refeito

### T-0701 - Recriar shell da aplicacao

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: frontend
- Dependencias: T-0503
- Entrega:
  - Layout operacional com navegacao.
  - Autenticacao/perfis se ja definida.
  - Views base:
    - Dashboard
    - Inbox
    - Upload manual
    - Validacao
    - Configuracoes
- Testes:
  - Build.
  - Testes de componentes.
- Criterio de aceite:
  - App abre sem depender de mocks hardcoded.

### T-0702 - Implementar upload manual

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: frontend, backend-com
- Dependencias: T-0102, T-0701
- Entrega:
  - Form de upload com metadados.
  - Preview de PDF/imagem.
  - Feedback de sucesso/erro.
- Testes:
  - Playwright: upload de PDF e imagem.
  - Carga UI leve: 20 uploads sequenciais automatizados.
- Criterio de aceite:
  - Usuario envia documento e ve protocolo/document_id.

### T-0703 - Implementar inbox e validacao humana

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: frontend, backend-core
- Dependencias: T-0503, T-0701
- Entrega:
  - Lista filtravel por estado.
  - Detalhe com documento original.
  - Campos extraidos editaveis.
  - Aprovar/rejeitar.
- Testes:
  - Playwright fluxo completo de validacao.
  - Acessibilidade basica.
- Criterio de aceite:
  - Operador aprova documento e core publica pedido de ERP.

### T-0704 - Implementar telas de configuracao

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: frontend, backend-core, backend-com
- Dependencias: T-0503, T-0103, T-0104
- Entrega:
  - Email accounts.
  - WhatsApp numbers.
  - Schemas/layouts.
  - ERP connectors.
- Testes:
  - CRUD por tela.
  - Permissao de supervisor.
- Criterio de aceite:
  - Supervisor configura canais sem editar `.env`.

## Fase 8 - Observabilidade, seguranca e operacao

### T-0801 - Logs, metricas e traces

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: todos
- Dependencias: fases de cada servico
- Entrega:
  - Logs JSON com `tenant_id`, `document_id`, `correlation_id`.
  - OpenTelemetry.
  - Dashboards basicos.
- Testes:
  - Trace E2E com um documento.
  - Metricas por modulo.
- Criterio de aceite:
  - Um documento pode ser rastreado do recebimento ao ERP.

### T-0802 - Seguranca e secrets

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: todos
- Dependencias: T-0004
- Entrega:
  - Remover segredos versionados.
  - `.env.example` sem credenciais reais.
  - Tokens/assinaturas para webhooks.
  - CORS restrito.
  - Autenticacao e autorizacao no core/frontend.
- Testes:
  - Requests sem token falham.
  - Webhook com assinatura invalida falha.
- Criterio de aceite:
  - Nenhuma credencial real em arquivos versionados.

## Fase 9 - Testes integrados e carga

### T-0901 - Testes E2E por canal

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: todos
- Dependencias: M1 a M7
- Entrega:
  - E2E Email -> ERP mock.
  - E2E WhatsApp -> ERP mock.
  - E2E Upload manual -> ERP mock.
- Testes:
  - Playwright + workers/event bus.
  - Asserts em estados finais.
- Criterio de aceite:
  - Todos os canais chegam a `erp.sent` com ERP mock.

### T-0902 - Testes de carga simulada por modulo

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: todos
- Dependencias: modulos isolados prontos
- Entrega:
  - Locust ou k6 em `tests/load/`.
  - Cenarios por modulo:
    - captura email
    - captura WhatsApp
    - upload manual
    - OCR com OpenRouter mock
    - layout classification
    - LangExtract mock
    - validacao core
    - ERP mock
- Testes:
  - Rodadas locais com defaults.
  - Rodadas CI com carga reduzida.
- Criterio de aceite:
  - Relatorio com throughput, P95, erro, backlog e gargalos.

### T-0903 - Teste de carga E2E com APIs externas mockadas

- Status: TODO
- Atualizado em: 2026-05-01
- Modulos: todos
- Dependencias: T-0901, T-0902
- Entrega:
  - Gerador de documentos fake.
  - OpenRouter mock.
  - Superlogica mock.
  - Twilio/email mock.
- Cenarios default:
  - 300 emails/hora.
  - 300 WhatsApps/hora.
  - 120 uploads/hora.
  - 2 MB por arquivo medio.
- Criterio de aceite:
  - Backlog estabiliza.
  - Erro <= 1%.
  - P95 de captura <= 2 s.
  - P95 de OCR mock <= 10 s.

## Ordem recomendada de execucao

1. T-0001, T-0002, T-0003, T-0004
2. T-0201, T-0202, T-0203
3. T-0101, T-0102
4. T-0204
5. T-0301, T-0302
6. T-0401, T-0402
7. T-0501, T-0502, T-0503, T-0504
8. T-0601, T-0602
9. T-0701, T-0702, T-0703, T-0704
10. T-0801, T-0802
11. T-0901, T-0902, T-0903

## Checklist de prontidao por modulo

### backend-com

- [ ] Health/readiness.
- [ ] Email webhook.
- [ ] Email IMAP fallback.
- [ ] WhatsApp webhook.
- [ ] Upload manual.
- [ ] Storage original.
- [ ] `document.received`.
- [ ] Testes unitarios.
- [ ] Testes de contrato.
- [ ] Testes de carga simulada.

### backend-ocr

- [ ] Bugs corrigidos.
- [ ] Perfil OpenRouter + Docling.
- [ ] API isolada preservada.
- [ ] Consumer `document.received`.
- [ ] Publisher `ocr.completed` e `ocr.failed`.
- [ ] Storage `raw_text_uri`.
- [ ] Testes OpenRouter mock.
- [ ] Testes Docling.
- [ ] Testes de carga simulada.

### layout-service

- [ ] API isolada.
- [ ] Consumer `ocr.completed`.
- [ ] Publisher `layout.classified`.
- [ ] Heuristicas iniciais.
- [ ] Fallback `generic`.
- [ ] Testes por layout.
- [ ] Testes de carga simulada.

### langextract-service

- [ ] API isolada.
- [ ] Consumer `layout.classified`.
- [ ] Publisher `extraction.completed`.
- [ ] Schemas versionados.
- [ ] Mock LLM.
- [ ] Testes por schema.
- [ ] Testes de carga simulada.

### backend-core

- [ ] Models e migracoes.
- [ ] Estado do documento.
- [ ] Consumers.
- [ ] APIs de inbox/detalhe/validacao.
- [ ] Publicacao `erp.integration.requested`.
- [ ] Idempotencia.
- [ ] Testes de transicao.
- [ ] Testes de carga de eventos.

### backend-conect

- [ ] API isolada.
- [ ] Consumer `erp.integration.requested`.
- [ ] Normalizador canonico.
- [ ] Mock ERP.
- [ ] Superlogica.
- [ ] Idempotencia.
- [ ] Retry/DLQ.
- [ ] Testes de carga simulada.

### frontend

- [ ] Shell da aplicacao.
- [ ] Upload manual.
- [ ] Inbox.
- [ ] Validacao.
- [ ] Configuracoes.
- [ ] Testes de componentes.
- [ ] Playwright.
- [ ] Testes de fluxo com backend mockado.

## Pendencias abertas

1. Escolher event bus.
2. Confirmar se Docling deve ser pacote real ou adaptador atual com `pypdfium2`.
3. Definir stack final do frontend: React/Vite mantido ou Next.js.
4. Fornecer credenciais e dados da secao "Dados e credenciais necessarios".
5. Definir metas reais de carga.
6. Definir campos canonicos do primeiro payload Superlogica.
7. Definir lista inicial de layouts e schemas.
