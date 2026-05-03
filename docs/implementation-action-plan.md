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
| Event bus | Redis Streams no ambiente integrado; adaptador local JSONL apenas para smoke/unit tests |
| Storage | MinIO em desenvolvimento, S3 compativel em producao; adaptador local para testes |
| OCR inicial | OpenRouter para imagens/PDFs escaneados; Docling para PDFs com texto |
| LangExtract | Microservico separado, sem misturar com OCR |
| ERP inicial | Export JSON local dos dados aprovados; `backend-conect` completo fica por ultimo, aguardando acesso Superlogica |
| Testes de carga | Locust ou k6, com cenarios simulados por canal |

## Dados e credenciais necessarios

Preencher antes das fases que dependem de integracoes reais.

### Obrigatorios para ambiente de desenvolvimento integrado

| Item | Necessario para | Valor a fornecer |
|------|-----------------|------------------|
| `OPENROUTER_API_KEY` | OCR via OpenRouter | `CONFIGURADO em docuparse-project/.env` |
| `OPENROUTER_MODEL` | OCR via OpenRouter | `CONFIGURADO em docuparse-project/.env` |
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
| Superlogica sandbox base URL | backend-conect completo | `PENDENTE` |
| Superlogica credenciais sandbox | backend-conect completo | `PENDENTE` |

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
| M0 | Contratos, compose base e dados de ambiente definidos | REVIEW |
| M1 | `backend-com` captura documentos e publica `document.received` | REVIEW |
| M2 | `backend-ocr` consome evento e publica `ocr.completed` | TODO |
| M3 | `layout-service` classifica layout e publica `layout.classified` | REVIEW |
| M4 | `langextract-service` extrai dados e publica `extraction.completed` | REVIEW |
| M5 | `backend-core` persiste estados e suporta validacao humana | REVIEW |
| M6 | Export JSON intermediario de payload aprovado; `backend-conect` completo aguardando Superlogica | REVIEW |
| M7 | Frontend novo suporta upload, inbox, validacao e configuracoes | REVIEW |
| M8 | Observabilidade, seguranca e testes de carga integrados | TODO |
| M9 | E2E por email, WhatsApp e upload manual ate ERP | TODO |

## Fase 0 - Fundacao e contratos

### T-0001 - Escolher event bus e storage

- Status: DONE
- Atualizado em: 2026-05-03
- Modulos: todos
- Dependencias: nenhuma
- Entrega:
  - Decisao documentada: Redis Streams para eventos integrados.
  - Decisao documentada: MinIO/S3 para storage integrado e adapter local para testes.
  - `docker-compose.yml` planejado com Redis, MinIO e Postgres.
- Testes:
  - Subir compose minimo com health checks.
  - Publicar e consumir evento fake.
- Criterio de aceite:
  - Um script local publica `document.received.fake` e outro consome.
- Evidencia:
  - `docuparse-project/shared/README.md`
  - `docuparse-project/shared/publish_fake_event.py`
  - `docuparse-project/shared/consume_fake_event.py`
  - `docuparse-project/shared/docuparse_events/__init__.py`
  - `docuparse-project/shared/tests/test_storage_and_events.py`
  - `DOCUPARSE_LOCAL_EVENT_DIR=/tmp/docuparse-events-test python shared/publish_fake_event.py`
  - `DOCUPARSE_LOCAL_EVENT_DIR=/tmp/docuparse-events-test python shared/consume_fake_event.py`
  - `pytest -q shared/tests`
  - `docker compose exec -T backend-com python -c "from docuparse_events import event_bus_from_env; print(event_bus_from_env().publish('document.received.smoke', {'event_type':'document.received.smoke','source':'backend-com'}))"`
  - `docker compose exec -T redis redis-cli XLEN document.received.smoke` retornou `1`.
- Pendencias:
  - Conectar consumidores persistentes dos servicos ao Redis Streams real.

### T-0002 - Definir contratos canonicos de eventos

- Status: DONE
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
- Evidencia:
  - `docuparse-project/contracts/events/schemas.py`
  - `docuparse-project/contracts/events/examples/`
  - `pytest -q contracts/tests shared/tests`
- Pendencias:
  - Empacotar/importar contratos em cada microservico quando os workers forem implementados.

### T-0003 - Definir modelo de storage e URIs

- Status: DONE
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
- Evidencia:
  - `docuparse-project/shared/docuparse_storage/__init__.py`
  - `pytest -q contracts/tests shared/tests`
- Pendencias:
  - Implementar adapter MinIO/S3 real e conectar backend-com/backend-ocr.

### T-0004 - Atualizar docker-compose base

- Status: REVIEW
- Atualizado em: 2026-05-02
- Modulos: infra
- Dependencias: T-0001
- Entrega:
  - `backend-com`, `backend-ocr`, `backend-core`, `layout-service`, `langextract-service`, `backend-conect`, `frontend`.
  - Postgres, event bus, storage, observabilidade basica.
  - Portas sem conflito.
  - Redis interno permanece em `redis:6379`; porta externa do host alterada para `6380` para evitar conflito com `redis-stack`.
  - `backend-core` usa Postgres no compose via variaveis `POSTGRES_*` e executa migracoes antes do runserver.
  - `backend-com` e `backend-core` compartilham volume `docuparse-storage` para resolver `local://...` no fluxo integrado.
  - Frontend em container usa proxy para `backend-core`/`backend-com` por nome de servico.
  - Healthchecks adicionados para servicos de aplicacao.
  - `backend-ocr` usa imagem padrao enxuta para container, sem Paddle/EasyOCR/Torch no build base.
  - `backend-com` publica eventos via Redis Streams no compose quando `DOCUPARSE_EVENT_BUS=redis`.
  - `backend-ocr` possui consumidor Redis Streams configuravel por `DOCUPARSE_OCR_WORKER_ENABLED`.
  - `layout-service` e `langextract-service` possuem consumidores Redis Streams configuraveis por flags no `.env`.
  - Profile `async-workers` contem servicos dedicados `backend-core-events`, `backend-ocr-worker`, `layout-worker` e `langextract-worker`.
  - `REDIS_URL` do compose pode ser sobrescrito por variavel de ambiente para smoke em DB isolado.
- Testes:
  - `docker compose up` sobe todos os health checks.
- Criterio de aceite:
  - Todos os servicos respondem `/health`.
- Evidencia:
  - `docuparse-project/docker-compose.yml`
  - `docuparse-project/README.md`
  - `docuparse-project/backend-core/core/settings.py`
  - `docuparse-project/backend-core/documents/views.py`
  - `docuparse-project/backend-ocr/requirements-container.txt`
  - `docker compose up --build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose config --quiet`
  - `docker compose up -d --build backend-com`
  - `docker compose exec -T redis redis-cli ping`
  - `lsof -nP -iTCP:6380 -sTCP:LISTEN`
  - `docker compose up -d --build backend-ocr`
  - `docker compose up -d --build layout-service langextract-service`
  - `docker compose exec -T backend-ocr python -c "from application.ocr_event_worker import worker_from_env; w=worker_from_env(); print(type(w.event_bus).__name__, type(w.storage).__name__, w.input_stream)"`
  - `docker compose --profile async-workers config --services`
  - `docker compose exec -T backend-ocr python -c "from application.run_worker import main; print('ocr worker module ok')"`
  - `docker compose exec -T layout-service python -c "from application.run_worker import main; print('layout worker module ok')"`
  - `docker compose exec -T langextract-service python -c "from application.run_worker import main; print('langextract worker module ok')"`
  - Smoke Redis DB 15:
    - publica `document.received` e `ocr.completed` simulados no Redis.
    - `docker compose exec -T -e DOCUPARSE_EVENT_BUS=redis -e REDIS_URL=redis://redis:6379/15 backend-core python manage.py consume_events --once --from-beginning`
    - `docker compose exec -T -e DOCUPARSE_EVENT_BUS=redis -e REDIS_URL=redis://redis:6379/15 -e DOCUPARSE_LAYOUT_WORKER_START_AT_LATEST=false layout-service python -m application.run_worker --once`
    - `docker compose exec -T -e DOCUPARSE_EVENT_BUS=redis -e REDIS_URL=redis://redis:6379/15 -e DOCUPARSE_EXTRACTION_WORKER_START_AT_LATEST=false langextract-service python -m application.run_worker --once`
    - documento smoke `e2ace546-3182-4925-87d4-be33eda4fff4` chegou a `EXTRACTION_COMPLETED` com schema `boleto` e campo `valor=R$ 123,45`.
  - Smoke Redis DB 14 com `backend-ocr-worker`:
    - publica apenas `document.received` com `data.metadata.ocr_mock_raw_text`.
    - `backend-core` consome `document.received`.
    - `backend-ocr` executa `python -m application.run_worker --once` com `DOCUPARSE_OCR_WORKER_ALLOW_MOCK=true`.
    - `layout-service` executa `python -m application.run_worker --once`.
    - `langextract-service` executa `python -m application.run_worker --once`.
    - `backend-core` consome eventos gerados e persiste documento `bd7df74c-efed-4803-af58-bcd523e09ba3` como `EXTRACTION_COMPLETED`, `engine_used=mock`, schema `boleto`, `valor=R$ 123,45`.
  - Smoke Redis DB 13 com profile `async-workers` long-running:
    - `env REDIS_URL=redis://redis:6379/13 DOCUPARSE_AUTO_PROCESS_OCR=false DOCUPARSE_OCR_WORKER_ALLOW_MOCK=true docker compose --profile async-workers up -d backend-core-events backend-ocr-worker layout-worker langextract-worker`
    - publica `document.received` com `ocr_mock_raw_text`.
    - workers long-running geram e consomem `ocr.completed`, `layout.classified` e `extraction.completed`.
    - documento smoke `901b7f0e-e38e-45b3-88da-a555f9b194f6` chegou a `EXTRACTION_COMPLETED`, `engine_used=mock`, schema `boleto`, `valor=R$ 123,45`.
    - workers de smoke foram parados com `docker compose --profile async-workers stop ...`.
  - `curl -s -i http://127.0.0.1:8000/api/ocr/health`
  - `curl -s -i http://127.0.0.1:8070/health`
  - `curl -s -i http://127.0.0.1:8080/health`
  - `curl -s -i http://127.0.0.1:8090/health`
  - `curl -s -i http://127.0.0.1:8091/health`
  - `curl -s -i http://127.0.0.1:5173`
  - `.venv/bin/python manage.py test documents` em `docuparse-project/backend-core`
  - `npm run build` em `docuparse-project/frontend`
- Pendencias:
  - Criar `backend-conect` dockerizavel antes de marcar DONE.
  - Definir quando a operacao padrao deve migrar do fluxo HTTP automatico para o profile `async-workers`.

## Fase 1 - Backend COM

### T-0101 - Transformar `backend-com` em microservico DocuParse

- Status: DONE
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
- Evidencia:
  - `docuparse-project/backend-com/src/backend_com/api/app.py`
  - `docuparse-project/backend-com/src/backend_com/services/document_ingest.py`
  - `docuparse-project/backend-com/Dockerfile`
  - `docuparse-project/backend-com/tests/test_backend_com_app.py`
  - `pytest -q tests` em `docuparse-project/backend-com`
  - `docker compose config --quiet`
  - `backend-com` reconstruido com dependencia `redis` e `DOCUPARSE_EVENT_BUS=redis` no compose.
- Pendencias:
  - Conectar storage MinIO/S3 real quando o adapter for implementado.

### T-0102 - Implementar upload manual

- Status: REVIEW
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
- Evidencia:
  - `docuparse-project/backend-com/src/backend_com/services/manual_upload.py`
  - `docuparse-project/backend-com/src/backend_com/api/app.py`
  - `docuparse-project/backend-com/tests/test_backend_com_app.py`
  - `pytest -q tests` em `docuparse-project/backend-com`
- Pendencias:
  - Teste de carga de 120 uploads/hora ainda pendente.
  - Endpoint usa adapters locais; integrar MinIO/Redis Streams reais.

### T-0103 - Implementar captura de email

- Status: REVIEW
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
- Evidencia:
  - `docuparse-project/backend-com/src/backend_com/services/email_capture.py`
  - `docuparse-project/backend-com/src/backend_com/services/document_ingest.py`
  - `docuparse-project/backend-com/src/backend_com/api/app.py`
  - `docuparse-project/backend-com/tests/test_backend_com_app.py`
  - `pytest -q tests` em `docuparse-project/backend-com`
- Pendencias:
  - Endpoint `/api/v1/email/messages` simula IMAP/polling via multipart; integrar IMAP real quando credenciais forem fornecidas.
  - Teste de carga de 300 emails/hora ainda pendente.

### T-0104 - Implementar captura de WhatsApp

- Status: REVIEW
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
- Evidencia:
  - `docuparse-project/backend-com/src/backend_com/services/whatsapp_capture.py`
  - `docuparse-project/backend-com/src/backend_com/services/document_ingest.py`
  - `docuparse-project/backend-com/src/backend_com/api/app.py`
  - `docuparse-project/backend-com/tests/test_backend_com_app.py`
  - `pytest -q tests` em `docuparse-project/backend-com`
- Pendencias:
  - Download real de `MediaUrl` Twilio depende de credenciais/acesso.
  - Validacao criptografica Twilio real ainda pendente; teste atual cobre token local opcional.
  - Teste de carga de 300 mensagens/hora ainda pendente.

## Fase 2 - Backend OCR

### T-0201 - Corrigir bugs do fluxo atual

- Status: DONE
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
- Evidencia:
  - `docuparse-project/backend-ocr/application/process_document.py`
  - `docuparse-project/backend-ocr/api/routes/document.py`
  - `docuparse-project/backend-ocr/api/schemas/ocr_schema.py`
  - `docuparse-project/backend-ocr/infrastructure/engines/tesseract_engine.py`
  - `docuparse-project/backend-ocr/tests/test_real_pdf_ocr.py`
  - `docs_teste/AnyScanner_12_09_2025.pdf` processado com `selected_engine=tesseract`: 1 pagina, `raw_text_len=1160`
  - `pytest -q tests` em `docuparse-project/backend-ocr`
- Pendencias:
  - Ampliar fixtures reais de imagem no proximo ciclo de OCR.

### T-0202 - Definir perfil OpenRouter + Docling

- Status: DONE
- Atualizado em: 2026-05-02
- Modulos: backend-ocr
- Dependencias: T-0201
- Entrega:
  - `digital_pdf -> docling`.
  - `scanned_image -> openrouter`.
  - `handwritten_complex -> openrouter`.
  - `backend-ocr` carrega `docuparse-project/.env` em startup local sem sobrescrever variaveis ja exportadas.
  - OpenRouter trata PDFs `scanned_image` e `handwritten_complex` como imagem; Docling fica restrito a `digital_pdf`.
  - OpenRouter faz segunda tentativa com `qwen/qwen2.5-vl-72b-instruct` quando imagem/PDF escaneado retorna `raw_text` vazio.
  - Classificacao de PDF textual preserva heuristica PyMuPDF do pipeline antigo:
    - `txtblocks > 0 and txtblocks >= imgblocks -> digital_pdf`.
  - Registry lazy real.
  - Engines legadas opcionais ficam fora do perfil operacional exibido em setup/listagem.
- Testes:
  - Resolver por content type.
  - Readiness falha sem `OPENROUTER_API_KEY` quando OpenRouter habilitado.
  - Roteamento automatico:
    - PDF texto -> `docling`.
    - PDF/imagem escaneado -> `openrouter`.
  - Fixture `26116062208629869000101000000000000625120022507574 - Condominio do Edificio Recife Colonial.pdf` classifica como `digital_pdf`.
- Criterio de aceite:
  - `GET /api/v1/engines` mostra apenas engines habilitadas e status real.
- Evidencia:
  - `docuparse-project/backend-ocr/domain/engine_resolver.py`
  - `docuparse-project/backend-ocr/infrastructure/engines/openrouter_engine.py`
  - `docuparse-project/backend-ocr/api/app.py`
  - `docuparse-project/backend-ocr/api/routes/document.py`
  - `docuparse-project/backend-ocr/tests/test_classifier.py`
  - `pytest -q tests/test_classifier.py tests/test_process_document_bugs.py` em `docuparse-project/backend-ocr`
  - `pytest -q tests/test_process_document_bugs.py tests/test_classifier.py` em `docuparse-project/backend-ocr`
  - `GET http://127.0.0.1:8080/api/v1/engines` retorna somente `docling`, `openrouter` e `tesseract`.
  - `GET http://127.0.0.1:8080/ready` retornou `ready`.
- Pendencias:
  - Teste real OpenRouter pode ser lento conforme modelo configurado; performance nao e criterio nesta etapa.

### T-0203 - Separar OCR de extracao semantica

- Status: DONE
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
- Evidencia:
  - `docuparse-project/backend-ocr/application/process_document.py`
  - `docuparse-project/backend-ocr/api/routes/document.py`
  - `docuparse-project/backend-ocr/api/schemas/ocr_schema.py`
  - `pytest -q tests` em `docuparse-project/backend-ocr`
- Pendencias:
  - Remover o modo legado apos `langextract-service` assumir a extracao em producao.

### T-0204 - Consumir `document.received` e publicar `ocr.completed`

- Status: REVIEW
- Atualizado em: 2026-05-03
- Modulos: backend-ocr
- Dependencias: T-0002, T-0003, T-0202, T-0203
- Entrega:
  - Worker/consumer do event bus.
  - Loop persistente `OCRWorker` para Redis Streams, controlado por `DOCUPARSE_OCR_WORKER_ENABLED`.
  - Servico dedicado `backend-ocr-worker` no profile `async-workers`.
  - Offset por stream em memoria do processo.
  - CLI `python -m application.run_worker --once` para smoke controlado.
  - Modo mock operacional protegido por `DOCUPARSE_OCR_WORKER_ALLOW_MOCK=true` e `data.metadata.ocr_mock_raw_text`.
  - Download do `file_uri`.
  - Storage de `raw_text.json`.
  - Publicacao `ocr.completed` ou `ocr.failed`.
- Testes:
  - Contrato entrada/saida.
  - Integracao com storage e event bus.
  - Carga simulada: 100 documentos/hora com OpenRouter mock.
- Criterio de aceite:
  - Evento `document.received` vira `ocr.completed` com `raw_text_uri`.
- Evidencia:
  - `docuparse-project/backend-ocr/application/ocr_event_worker.py`
  - `docuparse-project/backend-ocr/application/run_worker.py`
  - `docuparse-project/backend-ocr/api/app.py`
  - `docuparse-project/backend-ocr/requirements-container.txt`
  - `docuparse-project/backend-ocr/tests/test_ocr_event_worker.py`
  - `pytest -q tests/test_ocr_event_worker.py tests/test_classifier.py tests/test_process_document_bugs.py` em `docuparse-project/backend-ocr`
  - `pytest -q tests/test_ocr_event_worker.py` em `docuparse-project/backend-ocr`
  - `pytest -q shared/tests`
  - `docker compose up -d --build backend-ocr`
  - `curl -s -i http://127.0.0.1:8080/health`
- Pendencias:
  - Usar `backend-ocr-worker` no profile `async-workers` com `DOCUPARSE_AUTO_PROCESS_OCR=false` quando a virada assincrona for feita.
  - Conectar storage MinIO/S3 real; teste atual usa adapter local.
  - Carga simulada com OpenRouter mock ainda pendente.

## Fase 3 - Layout Service

### T-0301 - Criar microservico `layout-service`

- Status: REVIEW
- Atualizado em: 2026-05-03
- Modulos: layout-service
- Dependencias: T-0002, T-0003
- Entrega:
  - FastAPI health/readiness.
  - API isolada `POST /api/v1/classify-layout`.
  - Worker para consumir `ocr.completed`.
  - Loop persistente `LayoutWorker` para Redis Streams/local JSONL, controlado por `DOCUPARSE_LAYOUT_WORKER_ENABLED`.
  - Servico dedicado `layout-worker` no profile `async-workers`.
  - CLI `python -m application.run_worker --once` para smoke controlado.
- Testes:
  - Unitarios de heuristicas.
  - Contrato `layout.classified`.
- Criterio de aceite:
  - Texto bruto + document_type retorna layout e confidence.
- Evidencia:
  - `docuparse-project/layout-service/api/app.py`
  - `docuparse-project/layout-service/application/layout_event_worker.py`
  - `docuparse-project/layout-service/application/run_worker.py`
  - `docuparse-project/layout-service/Dockerfile`
  - `docuparse-project/layout-service/requirements.txt`
  - `docuparse-project/docker-compose.yml`
  - `pytest -q tests` em `docuparse-project/layout-service`
  - `docker compose up -d --build layout-service langextract-service`
  - `curl -s -i http://127.0.0.1:8090/health`
- Pendencias:
  - Usar `layout-worker` no profile `async-workers` somente na virada para fluxo assincrono.

### T-0302 - Implementar heuristicas iniciais de layout

- Status: REVIEW
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
- Evidencia:
  - `docuparse-project/layout-service/domain/classifier.py`
  - `docuparse-project/layout-service/tests/test_layout_service.py`
  - `pytest -q tests` em `docuparse-project/layout-service`
- Pendencias:
  - Rodar carga simulada de 500 classificacoes/min.
  - Ampliar fixtures reais por layout quando arquivos forem fornecidos.

## Fase 4 - LangExtract Service

### T-0401 - Criar microservico `langextract-service`

- Status: REVIEW
- Atualizado em: 2026-05-03
- Modulos: langextract-service
- Dependencias: T-0002, T-0003
- Entrega:
  - FastAPI health/readiness.
  - API isolada `POST /api/v1/extract`.
  - Worker para consumir `layout.classified`.
  - Loop persistente `ExtractionWorker` para Redis Streams/local JSONL, controlado por `DOCUPARSE_EXTRACTION_WORKER_ENABLED`.
  - Servico dedicado `langextract-worker` no profile `async-workers`.
  - CLI `python -m application.run_worker --once` para smoke controlado.
- Testes:
  - Contrato de request/response.
  - Mock LLM para testes deterministas.
- Criterio de aceite:
  - Texto + layout + schema gera `extraction.completed`.
- Evidencia:
  - `docuparse-project/langextract-service/api/app.py`
  - `docuparse-project/langextract-service/application/extraction_event_worker.py`
  - `docuparse-project/langextract-service/application/run_worker.py`
  - `docuparse-project/langextract-service/Dockerfile`
  - `docuparse-project/langextract-service/requirements.txt`
  - `docuparse-project/docker-compose.yml`
  - `pytest -q tests` em `docuparse-project/langextract-service`
  - `docker compose up -d --build layout-service langextract-service`
  - `curl -s -i http://127.0.0.1:8091/health`
- Pendencias:
  - Usar `langextract-worker` no profile `async-workers` somente na virada para fluxo assincrono.
  - Substituir/adaptar extrator deterministico para LLM mockado quando o provedor for definido.

### T-0402 - Implementar schemas versionados de extracao

- Status: REVIEW
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
- Evidencia:
  - `docuparse-project/langextract-service/domain/schemas.py`
  - `docuparse-project/langextract-service/domain/extractor.py`
  - `docuparse-project/langextract-service/tests/test_langextract_service.py`
  - `pytest -q tests` em `docuparse-project/langextract-service`
- Pendencias:
  - Validadores por campo ainda sao heuristicas simples.
  - Snapshot amplo de payload extraido e carga simulada de 100 extracoes/hora ainda pendentes.

## Fase 5 - Backend Core refeito

### T-0501 - Recriar modelo de dominio e persistencia

- Status: DONE
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
- Evidencia:
  - `docuparse-project/backend-core/documents/models.py`
  - `docuparse-project/backend-core/documents/migrations/0001_initial.py`
  - `docuparse-project/backend-core/documents/migrations/0002_rename_documents_d_tenant__718ecf_idx_documents_d_tenant__1461e3_idx_and_more.py`
  - `docuparse-project/backend-core/documents/tests/test_models.py`
  - `.venv/bin/python manage.py test documents` em `docuparse-project/backend-core`
  - `docker compose exec -T backend-core python manage.py makemigrations --check --dry-run`
  - `docker compose exec -T backend-core python manage.py migrate --noinput`
- Pendencias:
  - Migrar banco de desenvolvimento quando o Postgres do compose estiver em uso.

### T-0502 - Implementar consumidores de eventos do core

- Status: DONE
- Atualizado em: 2026-05-03
- Modulos: backend-core
- Dependencias: T-0501
- Entrega:
  - Consome `document.received`, `ocr.completed`, `ocr.failed`, `extraction.completed`, `erp.sent`, `erp.failed`.
  - Atualiza estados.
  - Cria pendencias de validacao.
  - Disponibiliza worker persistente `manage.py consume_events` para consumir Redis Streams/local JSONL fora do request HTTP.
  - Prepara servico opcional `backend-core-events` no profile `async-workers` do Docker Compose.
- Testes:
  - Contratos de eventos.
  - Idempotencia por `event_id` ou chave equivalente.
  - Carga simulada: 1000 eventos/min com event bus local.
- Criterio de aceite:
  - Reprocessar o mesmo evento nao duplica documento/estado.
- Evidencia:
  - `docuparse-project/backend-core/documents/services/event_consumers.py`
  - `docuparse-project/backend-core/documents/services/event_stream_worker.py`
  - `docuparse-project/backend-core/documents/management/commands/consume_events.py`
  - `docuparse-project/backend-core/documents/tests/test_event_consumers.py`
  - `docuparse-project/backend-core/documents/tests/test_event_stream_worker.py`
  - `docuparse-project/docker-compose.yml`
  - `.venv/bin/python manage.py test documents` em `docuparse-project/backend-core`
  - `.venv/bin/python manage.py consume_events --once` em `docuparse-project/backend-core`
  - `docker compose config --quiet` em `docuparse-project`
  - `docker compose up -d --build backend-core` em `docuparse-project`
  - `docker compose exec -T backend-core python manage.py consume_events --once` retornou `Processed 0 event(s).`
  - `docker compose ps` com `backend-core`, `backend-com`, `backend-ocr`, `redis`, `postgres`, `minio`, `layout-service`, `langextract-service` saudaveis.
  - Consumidores `consume_ocr_completed` e `consume_ocr_failed` atualizam `raw_text_uri`, `document_type`, metadados OCR e estado do documento com idempotencia por `event_id`.
- Pendencias:
  - Habilitar o profile `async-workers` quando a virada para fluxo totalmente assincrono for feita.
  - Criar DLQ/retry operacional para falhas de processamento.

### T-0503 - Implementar APIs para frontend

- Status: DONE
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
- Evidencia:
  - `docuparse-project/backend-core/documents/views.py`
  - `docuparse-project/backend-core/documents/serializers.py`
  - `docuparse-project/backend-core/documents/urls.py`
  - `docuparse-project/backend-core/documents/tests/test_api.py`
  - `.venv/bin/python manage.py test documents` em `docuparse-project/backend-core`
- Pendencias:
  - Autenticacao/autorizacao por perfil ainda precisa ser endurecida na Fase 8.

### T-0504 - Publicar `erp.integration.requested`

- Status: DONE
- Atualizado em: 2026-05-03
- Modulos: backend-core, backend-conect
- Dependencias: T-0503
- Entrega:
  - Ao aprovar, core publica evento de ERP.
  - Publicacao usa `event_bus_from_env`, permitindo Redis Streams no compose e JSONL local nos testes.
  - Ao aprovar, core exporta payload canonico para arquivo JSON local.
  - Estado muda para `ERP_INTEGRATION_REQUESTED`.
- Testes:
  - Aprovar documento gera um evento.
  - Aprovar documento gera um arquivo JSON com os dados aprovados.
  - Rejeitar documento nao gera evento ERP.
- Criterio de aceite:
  - `backend-conect` consegue consumir evento aprovado.
- Evidencia:
  - `docuparse-project/backend-core/documents/services/approved_exporter.py`
  - `docuparse-project/backend-core/documents/services/erp_publisher.py`
  - `docuparse-project/backend-core/documents/views.py`
  - `docuparse-project/backend-core/documents/tests/test_api.py`
  - `.venv/bin/python manage.py test documents` em `docuparse-project/backend-core`
- Pendencias:
  - Export JSON e solucao intermediaria ate haver acesso ao Superlogica.

## Fase 6 - Backend CONECT

### T-0550 - Exportar dados aprovados para JSON intermediario

- Status: DONE
- Atualizado em: 2026-05-01
- Modulos: backend-core
- Dependencias: T-0503
- Entrega:
  - Exportar payload canonico aprovado para arquivo `.json`.
  - Diretório configuravel por `DOCUPARSE_APPROVED_EXPORT_DIR`.
  - Nome deterministico por tenant/documento.
- Testes:
  - Aprovar documento gera JSON com `document_id`, `tenant_id`, `correlation_id` e `payload.fields`.
- Criterio de aceite:
  - Operacao nao depende de Superlogica nem de `backend-conect`.
- Evidencia:
  - `docuparse-project/backend-core/documents/services/approved_exporter.py`
  - `docuparse-project/backend-core/documents/tests/test_api.py`
  - `.venv/bin/python manage.py test documents` em `docuparse-project/backend-core`
- Pendencias:
  - Definir destino definitivo do arquivo em ambiente integrado/operacional.

### T-0601 - Criar microservico `backend-conect`

- Status: BLOCKED
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
- Evidencia:
  - Adiado por decisao de projeto: export JSON intermediario cobre aprovados ate acesso Superlogica.
- Pendencias:
  - Retomar quando campos canonicos e acesso Superlogica estiverem definidos.

### T-0602 - Implementar conector Superlogica e mock ERP

- Status: BLOCKED
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
- Evidencia:
  - Bloqueado por falta de acesso Superlogica.
- Pendencias:
  - Fornecer `Superlogica sandbox base URL` e credenciais sandbox.

## Fase 7 - Frontend refeito

### T-0701 - Recriar shell da aplicacao

- Status: DONE
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
- Evidencia:
  - `docuparse-project/frontend/src/main.jsx`
  - `docuparse-project/frontend/src/index.css`
  - `docuparse-project/frontend/vite.config.js`
  - `npm run build` em `docuparse-project/frontend`
- Pendencias:
  - Autenticacao/perfis ainda nao definidos; tela opera sem login ate Fase 8.

### T-0702 - Implementar upload manual

- Status: REVIEW
- Atualizado em: 2026-05-02
- Modulos: frontend, backend-com, backend-core
- Dependencias: T-0102, T-0701
- Entrega:
  - Form de upload com metadados.
  - Preview de PDF/imagem.
  - Feedback de sucesso/erro.
  - Sincronizacao local best-effort do `document.received` para o `backend-core` apos upload, permitindo aparicao imediata no Dashboard/Inbox.
- Testes:
  - Playwright: upload de PDF e imagem.
  - Carga UI leve: 20 uploads sequenciais automatizados.
  - Upload manual direto com `docs_teste/AnyScanner_12_09_2025.pdf` retorna `core_sync_status: synced:201`.
- Criterio de aceite:
  - Usuario envia documento e ve protocolo/document_id.
  - Documento enviado aparece no Dashboard/Inbox do `backend-core`.
- Evidencia:
  - `docuparse-project/frontend/src/main.jsx`
  - `docuparse-project/frontend/vite.config.js`
  - `docuparse-project/backend-com/src/backend_com/services/document_ingest.py`
  - `docuparse-project/backend-core/documents/views.py`
  - `docuparse-project/backend-core/documents/urls.py`
  - `docuparse-project/backend-core/documents/tests/test_api.py`
  - `docuparse-project/backend-com/tests/test_backend_com_app.py`
  - `npm run build` em `docuparse-project/frontend`
  - `pytest -q tests` em `docuparse-project/backend-com`
  - `.venv/bin/python manage.py test documents` em `docuparse-project/backend-core`
- Pendencias:
  - Playwright com upload de PDF/imagem ainda pendente.
  - Carga UI leve de 20 uploads sequenciais ainda pendente.

### T-0703 - Implementar inbox e validacao humana

- Status: REVIEW
- Atualizado em: 2026-05-02
- Modulos: frontend, backend-core, backend-ocr
- Dependencias: T-0503, T-0701
- Entrega:
  - Lista filtravel por estado.
  - Detalhe com documento original.
  - Preview do arquivo original via endpoint do `backend-core`.
  - OCR automatico em background quando `backend-core` recebe `document.received` do `backend-com`.
  - Metadados do OCR exibidos na validacao:
    - engine utilizado
    - classificacao do documento
    - hint aplicado de `CLASSIFICATION_ENGINE_PREPROCESSING_HINTS`
  - Transcricao completa exibida em campo separado dos campos extraidos/editaveis.
  - Campos extraidos editaveis.
  - Acoes operacionais na validacao:
    - reprocessar OCR do documento existente.
    - excluir documento somente da aplicacao, preservando os arquivos locais para auditoria/reprocessamento externo.
  - Aprovar/rejeitar.
- Testes:
  - Playwright fluxo completo de validacao.
  - Acessibilidade basica.
  - Endpoint de arquivo original.
  - Endpoint de processamento OCR com mock em teste unitario.
  - Endpoint de reprocessamento OCR substitui campos/transcricao existentes.
  - Endpoint de exclusao remove registro da aplicacao e preserva arquivo local.
  - Evento `document.received` inicia OCR automatico quando habilitado.
  - Roteamento `scanned_image -> openrouter` expõe hint `render_pdf_or_image_for_vision_ocr`.
  - PDF textual com `76` blocos de texto e `3` de imagem classifica como `digital_pdf` e transcreve por `docling` com fallback textual PyMuPDF quando `pypdfium2` nao esta instalado.
  - Imagem OCR via OpenRouter recupera transcricao a partir de `key_values` quando `extracted_text` vem vazio.
  - Tela de validacao exibe estado transitorio `reclassificando...` durante reprocessamento e sincroniza lista/detalhe com a classificacao retornada pela API.
- Criterio de aceite:
  - Operador aprova documento e core publica pedido de ERP.
  - Documento carregado por email, WhatsApp ou upload manual pode ser visualizado e recebe OCR automaticamente antes da aprovacao.
  - Operador consegue reprocessar ou excluir documento sem acessar banco/arquivos manualmente.
- Evidencia:
  - `docuparse-project/frontend/src/main.jsx`
  - `docuparse-project/backend-core/documents/views.py`
  - `docuparse-project/backend-core/documents/urls.py`
  - `docuparse-project/backend-core/documents/services/ocr_client.py`
  - `docuparse-project/backend-core/documents/services/ocr_processor.py`
  - `docuparse-project/backend-core/documents/serializers.py`
  - `docuparse-project/backend-ocr/domain/classifier.py`
  - `docuparse-project/backend-ocr/infrastructure/engines/openrouter_engine.py`
  - `docuparse-project/backend-ocr/infrastructure/engines/docling_engine.py`
  - `docuparse-project/backend-ocr/application/process_document.py`
  - `docuparse-project/backend-ocr/api/schemas/ocr_schema.py`
  - `docuparse-project/backend-core/documents/tests/test_api.py`
  - `docuparse-project/backend-ocr/tests/test_process_document_bugs.py`
  - `npm run build` em `docuparse-project/frontend`
  - `.venv/bin/python manage.py test documents` em `docuparse-project/backend-core`
  - `npm run build` em `docuparse-project/frontend`
  - `pytest -q tests/test_process_document_bugs.py` em `docuparse-project/backend-ocr`
  - `pytest -q tests/test_classifier.py tests/test_process_document_bugs.py` em `docuparse-project/backend-ocr`
  - `npm run build` em `docuparse-project/frontend` apos sincronizacao de estado do reprocessamento.
  - `docs_teste/26116062208629869000101000000000000625120022507574 - Condominio do Edificio Recife Colonial.pdf`: `digital_pdf`, engine `docling`, transcricao com `2624` caracteres.
  - `docs_teste/PHOTO-2026-01-08-18-44-00.jpg`: `scanned_image`, engine `openrouter`, transcricao reconstruida dos `key_values` apos reprocessamento.
  - API de detalhe retorna `full_transcription` separado; campos editaveis nao recebem mais transcricao longa em `retencao`.
- Pendencias:
  - Playwright de fluxo completo de validacao ainda pendente.
  - Acessibilidade basica ainda pendente.
  - Evoluir OCR automatico de thread local para worker/event bus persistente.

### T-0704 - Implementar telas de configuracao

- Status: REVIEW
- Atualizado em: 2026-05-02
- Modulos: frontend, backend-core, backend-com
- Dependencias: T-0503, T-0103, T-0104
- Entrega:
  - Email accounts.
  - WhatsApp numbers.
  - Schemas/layouts.
  - Abas guiadas de setup LangExtract conforme `docs/specs/lang_extract_prd.md`:
    - setup do modelo/versionamento/status.
    - hierarquia com `Modelo` como aba principal; OCR, Schema, Instrucoes, Exemplos, Teste, Regras e Publicacao herdam o modelo ativo.
    - cabecalho `Modelo ativo` nas abas subordinadas com schema, versao, layout, tipo e status.
    - botoes `Salvar rascunho` e `Salvar e ir para proxima etapa` nas abas subordinadas.
    - endpoint `PATCH /schema-configs/{id}` para atualizar `SchemaConfig.definition` sem duplicar versoes.
    - OCR de referencia com documento original e transcricao.
    - revisao da qualidade do OCR de referencia, com status, acao recomendada e observacoes.
    - schema de campos com tipo, obrigatoriedade e regra, indicando explicitamente o schema/versao em edicao.
    - carregamento de schema existente como base para edicao guiada.
    - listagem de schemas/layouts existentes concentrada na aba Setup para nao poluir as demais etapas.
    - instrucoes/prompt com hints reutilizaveis.
    - exemplos few-shot anotados.
    - teste visual com original, OCR destacado e preview JSON.
    - regras de pos-processamento.
    - publicacao do schema e vinculo de layout.
  - Cada aba de configuracao exibe orientacao superior explicando o objetivo e como preencher os campos.
  - Configuracoes separadas por dominio:
    - Email
    - WhatsApp
    - OCR
    - Extracao
    - Integracoes
  - Telas operacionais iniciais para OCR, Email, WhatsApp e Integracoes com campos estruturados e orientacao de uso.
  - Aba OCR mostra somente engines em uso real: Docling, OpenRouter e Tesseract fallback.
  - ERP connectors.
- Testes:
  - CRUD por tela.
  - Permissao de supervisor.
  - Build frontend apos inclusao das abas LangExtract.
- Criterio de aceite:
  - Supervisor configura canais sem editar `.env`.
  - Supervisor consegue montar um template LangExtract auditavel sem editar prompt livre isolado.
- Evidencia:
  - `docuparse-project/frontend/src/main.jsx`
  - `npm run build` em `docuparse-project/frontend`
  - `npm run build` em `docuparse-project/frontend` apos textos de ajuda por aba.
  - `npm run build` em `docuparse-project/frontend` apos revisao de qualidade do OCR de referencia.
  - `npm run build` em `docuparse-project/frontend` apos seletor de schema ativo na aba Schema.
  - `npm run build` em `docuparse-project/frontend` apos mover cards de schemas/layouts para Setup.
  - `npm run build` em `docuparse-project/frontend` apos hierarquia `Modelo` + subabas dependentes do contexto ativo.
  - `.venv/bin/python manage.py test documents` apos endpoint de rascunho.
  - `npm run build` em `docuparse-project/frontend` apos botoes de rascunho/proxima etapa.
  - `npm run build` em `docuparse-project/frontend` apos dividir Configuracoes em Extracao/OCR/Email/WhatsApp/Integracoes.
  - `npm run build` em `docuparse-project/frontend` apos remover OCRs opcionais/legados da aba OCR.
  - `docs/specs/lang_extract_prd.md`
- Pendencias:
  - CRUD visual implementado para schemas/layouts e setup guiado LangExtract persistindo em `SchemaConfig.definition`.
  - Tabelas dedicadas do PRD (`extraction_template`, `extraction_prompt`, `extraction_example`, `extraction_run`, etc.) ainda precisam de modelo/API antes de substituir a persistencia temporaria em JSON.
  - Revisao do OCR de referencia e observacoes ficam temporariamente em `SchemaConfig.definition.reference_review`.
  - Destaque visual por coordenadas diretamente sobre PDF/imagem depende de OCR salvar bounding boxes/spans; tela atual destaca o OCR textual e mostra o original lado a lado.
  - Email accounts, WhatsApp numbers e ERP connectors ainda precisam de APIs/modelos definitivos.
  - Telas OCR, Email, WhatsApp e Integracoes ainda nao persistem em backend; proximas tarefas devem criar modelos/API para substituir `.env`/config local.
  - Permissao de supervisor ainda pendente ate autenticacao/autorizacao.

## Fase 8 - Observabilidade, seguranca e operacao

### T-0801 - Logs, metricas e traces

- Status: REVIEW
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
- Evidencia:
  - `docuparse-project/shared/docuparse_observability/__init__.py`
  - Logs JSON instrumentados em:
    - `backend-com` publica `document.received`
    - `backend-ocr` publica `ocr.completed`/`ocr.failed`
    - `layout-service` publica `layout.classified`
    - `langextract-service` publica `extraction.completed`
    - `backend-core` consome eventos e publica/exporta ERP
  - `pytest -q contracts/tests shared/tests`
  - `pytest -q tests` em `backend-com`, `backend-ocr`, `layout-service`, `langextract-service`
  - `.venv/bin/python manage.py test documents` em `backend-core`
- Pendencias:
  - OpenTelemetry ainda pendente.
  - Dashboards basicos ainda pendentes.
  - Trace E2E real depende dos workers Redis Streams integrados.

### T-0802 - Seguranca e secrets

- Status: REVIEW
- Atualizado em: 2026-05-02
- Modulos: todos
- Dependencias: T-0004
- Entrega:
  - Remover segredos versionados.
  - `.env.example` sem credenciais reais.
  - Tokens/assinaturas para webhooks:
    - `backend-com` valida `DOCUPARSE_EMAIL_WEBHOOK_TOKEN` e `DOCUPARSE_WHATSAPP_WEBHOOK_TOKEN` quando configurados.
    - Upload manual do `backend-com` valida `DOCUPARSE_INTERNAL_SERVICE_TOKEN` quando configurado.
  - CORS restrito:
    - `backend-ocr` e `backend-com` usam `CORS_ALLOWED_ORIGINS`, com default local para Vite.
  - Autenticacao e autorizacao no core/frontend:
    - `backend-core` valida `DOCUPARSE_INTERNAL_SERVICE_TOKEN` nas rotas operacionais quando configurado.
- Testes:
  - `pytest -q tests` em `backend-com` cobrindo upload manual sem token e webhooks com assinatura invalida.
  - `.venv/bin/python manage.py test documents` em `backend-core` cobrindo request sem token.
  - `pytest -q tests` em `backend-ocr` apos ajuste de CORS.
- Criterio de aceite:
  - Nenhuma credencial real em arquivos versionados.
- Pendencias:
  - Revisao completa de arquivos `.env` locais antes de commit/publicacao.
  - Autenticacao de usuario real no frontend/core.
  - CORS do `backend-core` depende da estrategia final de deploy/proxy.

## Fase 9 - Testes integrados e carga

### T-0901 - Testes E2E por canal

- Status: REVIEW
- Atualizado em: 2026-05-03
- Modulos: todos
- Dependencias: M1 a M7
- Entrega:
  - E2E Email -> ERP mock:
    - `backend-core/documents/tests/test_e2e_local_pipeline.py`
  - E2E WhatsApp -> ERP mock:
    - `backend-core/documents/tests/test_e2e_local_pipeline.py`
  - E2E Upload manual -> ERP mock:
    - `backend-core/documents/tests/test_e2e_local_pipeline.py`
  - ERP mock local:
    - `backend-core/documents/services/erp_mock.py` consome `erp.integration.requested` e publica `erp.sent`.
  - Fluxo validado:
    - captura `backend-com`
    - `document.received`
    - consumo no `backend-core`
    - `extraction.completed` simulada
    - aprovacao
    - export JSON aprovado
    - `erp.sent` mockado
  - Smoke assincrono parcial por Redis DB 15:
    - `document.received` e `ocr.completed` simulados.
    - `layout-service` real processa `ocr.completed`.
    - `langextract-service` real processa `layout.classified`.
    - `backend-core` real consome `extraction.completed` e persiste `ExtractionResult`.
  - Smoke assincrono com OCR worker mockado por Redis DB 14:
    - `backend-ocr-worker` real consome `document.received` e publica `ocr.completed`.
    - `layout-service`, `langextract-service` e `backend-core` processam a cadeia gerada.
  - Smoke assincrono long-running com profile `async-workers` por Redis DB 13:
    - `backend-core-events`, `backend-ocr-worker`, `layout-worker` e `langextract-worker` ficaram rodando como processos independentes.
    - documento `901b7f0e-e38e-45b3-88da-a555f9b194f6` chegou a `EXTRACTION_COMPLETED`.
- Testes:
  - `.venv/bin/python manage.py test documents` em `backend-core`.
  - Asserts em estados finais `ERP_SENT`, tentativa ERP `sent`, arquivo JSON exportado e evento `erp.sent`.
- Criterio de aceite:
  - Todos os canais chegam a `erp.sent` com ERP mock.
- Pendencias:
  - Rodar OCR real com fixture controlada quando o custo/latencia do provedor externo estiver aceitavel.
  - Adicionar Playwright cobrindo o frontend e validacao manual pela UI.

### T-0902 - Testes de carga simulada por modulo

- Status: REVIEW
- Atualizado em: 2026-05-02
- Modulos: todos
- Dependencias: modulos isolados prontos
- Entrega:
  - Simulador local sem dependencias externas em `tests/load/simulate_module_load.py`.
  - Cenarios por modulo:
    - captura email: `email_capture`
    - captura WhatsApp: `whatsapp_capture`
    - upload manual: `manual_upload`
    - OCR com OpenRouter mock: `ocr_mock`
    - layout classification: `layout_mock`
    - LangExtract mock: `langextract_mock`
    - ERP mock
- Testes:
  - Rodada local:
    - `backend-core/.venv/bin/python tests/load/simulate_module_load.py --scenario all --iterations 5 --concurrency 2`
  - Relatorio JSON inclui `throughput_per_second`, `p95_ms`, erros, amostra de erros e backlog por stream.
- Criterio de aceite:
  - Relatorio com throughput, P95, erro, backlog e gargalos.
- Pendencias:
  - Adicionar cenario de validacao core com banco isolado.
  - Rodadas maiores para gerar baseline real.
  - Avaliar Locust ou k6 quando as APIs estiverem expostas de forma estavel.

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

### todos

- [x] Logs JSON com `tenant_id`, `document_id`, `correlation_id` nos eventos principais.
- [x] Token interno opcional em `backend-core` e upload manual do `backend-com`.
- [x] CORS configuravel por `CORS_ALLOWED_ORIGINS` em `backend-ocr` e `backend-com`.
- [x] Tokens locais opcionais para webhooks de email/WhatsApp.
- [ ] Autenticacao de usuario real no frontend/core.
- [ ] Revisao final de secrets e `.env.example`.
- [ ] OpenTelemetry.
- [ ] Dashboards basicos.

### backend-com

- [x] Health/readiness.
- [x] Email webhook.
- [x] Email IMAP fallback.
- [x] WhatsApp webhook.
- [x] Upload manual.
- [x] Storage original.
- [x] `document.received`.
- [x] Testes unitarios.
- [x] Testes de contrato.
- [x] E2E local ate `erp.sent` mockado para email, WhatsApp e upload manual.
- [x] Testes de carga simulada local.

### backend-ocr

- [x] Bugs corrigidos.
- [x] Perfil OpenRouter + Docling.
- [x] API isolada preservada.
- [x] Consumer `document.received`.
- [x] Publisher `ocr.completed` e `ocr.failed`.
- [x] Storage `raw_text_uri`.
- [ ] Testes OpenRouter mock.
- [ ] Testes Docling.
- [ ] Testes de carga simulada.

### layout-service

- [x] API isolada.
- [x] Consumer `ocr.completed`.
- [x] Publisher `layout.classified`.
- [x] Heuristicas iniciais.
- [x] Fallback `generic`.
- [x] Testes por layout.
- [ ] Testes de carga simulada.

### langextract-service

- [x] API isolada.
- [x] Consumer `layout.classified`.
- [x] Publisher `extraction.completed`.
- [x] Schemas versionados.
- [ ] Mock LLM.
- [x] Testes por schema.
- [ ] Testes de carga simulada.

### backend-core

- [x] Models e migracoes.
- [x] Estado do documento.
- [x] Consumers.
- [x] APIs de inbox/detalhe/validacao.
- [x] Publicacao `erp.integration.requested`.
- [x] Export JSON de dados aprovados.
- [x] Idempotencia.
- [x] Testes de transicao.
- [ ] Testes de carga de eventos.

### backend-conect

- [ ] API isolada.
- [ ] Consumer `erp.integration.requested`.
- [ ] Normalizador canonico.
- [ ] Mock ERP.
- [ ] Superlogica. `BLOCKED`: sem acesso/credenciais.
- [ ] Idempotencia.
- [ ] Retry/DLQ.
- [ ] Testes de carga simulada.

### frontend

- [x] Shell da aplicacao.
- [x] Upload manual.
- [x] Inbox.
- [x] Validacao.
- [x] Configuracoes.
- [ ] Testes de componentes.
- [ ] Playwright.
- [ ] Testes de fluxo com backend mockado.

## Pendencias abertas

1. Conectar workers/publicadores ao Redis Streams real.
2. Confirmar se Docling deve ser pacote real ou adaptador atual com `pypdfium2`.
3. Definir stack final do frontend: React/Vite mantido ou Next.js.
4. Fornecer credenciais e dados da secao "Dados e credenciais necessarios".
5. Definir metas reais de carga.
6. Definir campos canonicos do primeiro payload Superlogica.
7. Ampliar lista inicial de layouts e schemas com fixtures reais.
8. Definir destino operacional dos exports JSON aprovados.
