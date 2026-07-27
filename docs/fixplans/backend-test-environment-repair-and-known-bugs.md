# Reparo dos ambientes de dev/teste dos backends + bugs conhecidos

> Status: ambientes de dev/teste corrigidos e commitados (`2714129`, `6e74b67` na branch `016-frontend-architecture-refactor`). Os bugs listados na §2 **não foram corrigidos** — ficam registrados aqui para tratamento futuro.
> Contexto: o pedido original era "os testes não rodam bem, deve ser falta de backend". Investigação mostrou que os 4 backends (backend-core:8000, backend-com:8070, backend-ocr:8080, langextract-service:8091) realmente estavam parcialmente fora do ar por variáveis de `.env` faltando, mas a causa das falhas de teste era outra: cada serviço tinha dependências de dev/teste não declaradas ou desatualizadas, além de alguns bugs reais de aplicação que as suítes acabaram expondo depois que o ambiente ficou utilizável.

---

## 1. O que foi corrigido (ambiente)

### 1.1 `.env` — variáveis faltando para o backend-core subir

O `start_backend.sh` roda `manage.py migrate && manage.py seed_data && manage.py runserver`. O `seed_data` abortava com `CommandError`, e como é `&&`, o `runserver` nunca era alcançado — por isso a porta 8000 nunca respondia.

Adicionado a `/docuparser/.env` (não versionado, está no `.gitignore`):
```
ADMIN_EMAIL=admin@docuparse.com
ADMIN_PASSWORD=admin12345
DEFAULT_TENANT_SLUG=default
DEFAULT_TENANT_NAME=Default Tenant
```
Ver `users/management/commands/seed_data.py:34-43`.

### 1.2 backend-core — faltavam `boto3`, `moto`, `pytest-django`

- `pyproject.toml` não declarava nenhum grupo de dependências de dev/teste. `documents/tests/test_migrate_storage_command.py` e `test_storage_cross_service.py` importam `boto3`/`moto` diretamente e quebravam a coleta do pytest.
- Mais importante: **sem `pytest-django`, o pytest não cria um banco de teste isolado.** Os `TestCase` do Django rodavam contra o banco Postgres real de dev (o mesmo populado pelo `seed_data`), causando `UniqueViolation` em massa ao tentar recriar permissions como `documents.validate` que já existiam. Rodar com `manage.py test` (que cria banco de teste sozinho) mascarava esse problema mas expunha outro: sem a fixture `_reset_tenant_schema` do `conftest.py` (que só roda sob pytest), o schema de tenant vazava de um teste pro outro (`Exception: Can't create tenant outside the public schema`).
- Correção: `uv add --group dev "boto3>=1.34.0" "moto[s3]>=5.0" "pytest-django>=4.9.0" "pytest>=9.1.1"` em `docuparse-project/backend-core/pyproject.toml`.
- Runner correto a partir de agora: **`uv run pytest`**, não `manage.py test`.

### 1.3 backend-com — imports `backend_com.*` quebrados + `httpx` faltando

- O pacote é instalado via editable install que só adiciona o diretório `backend-com/` ao `sys.path` (ver `.venv/lib/python3.13/site-packages/_editable_impl_backend_com.pth`), sem criar um pacote `backend_com`. Isso significa que os módulos são importáveis "flat" (`config`, `services.X`, `api.X`), **não** como `backend_com.config`, `backend_com.services.X`.
- `services/document_ingest.py:10` já tinha sido corrigido (`from config import settings`) antes de eu investigar, mas os testes ainda usavam o import antigo. Corrigido em `tests/test_backend_com_app.py` e `tests/test_ingest_storage_failure.py` (imports `backend_com.X` → `X`).
- `starlette.testclient` exige `httpx` (ou `httpx2`) instalado; não estava. Adicionado `httpx>=0.28.1` ao extra `test` de `pyproject.toml`.
- **Nota de arquitetura**: o layout "flat" (sem pacote `backend_com`) parece intencional dado o `.pth` de editable install, mas o nome `backend_com` ainda aparece espalhado pelo repo como se fosse um pacote de verdade — ver §2.4.

### 1.4 backend-ocr — script de debug travava a suíte inteira

- `run_real_test.py` era um script manual de um dev (`/Users/dirceusilva/Documents/...`, caminho do Mac dele), não um teste — mas o nome batia no padrão de coleta `*_test.py` do pytest. O script chama `exit(1)` na primeira linha executável se o arquivo hardcoded não existir, o que derruba a *sessão inteira* do pytest com `INTERNALERROR`.
- Renomeado para `manual_ocr_check.py` (fora do padrão de coleta). Nenhuma lógica alterada.

### 1.5 langextract-service — venv nunca sincronizado

- `uv sync` nunca tinha rodado nesse serviço (faltava até `pydantic`, uma dependência direta declarada no `pyproject.toml`).
- `pytest` e `httpx` (mesma exigência do `TestClient`) não estavam declarados em nenhum grupo. Adicionados via `uv add --group dev "pytest>=9.1.1" "httpx>=0.28.1"`.

### 1.6 Resultado após as correções de ambiente

| Serviço | Antes | Depois |
|---|---|---|
| backend-core | suíte não coletava de forma confiável / rodava com runner errado | 134 passam / 7 falham (pytest) |
| backend-com | não coletava (`ModuleNotFoundError`, faltava `httpx`) | 17 passam / 1 falha |
| backend-ocr | `INTERNALERROR`, suíte inteira travava | 14 passam / 10 falham |
| langextract-service | não coletava (faltava `pydantic`) | 6 passam / 0 falham |

### 1.7 Armadilha de ambiente a evitar (não é bug de código)

Rodar `uv run pytest` num shell onde `export $(grep -v '^#' .env | xargs)` já exportou `DOCUPARSE_EVENT_BUS=redis` faz `event_bus_from_env()` (`shared/docuparse_events/__init__.py:126-134`) ler `os.environ` diretamente e construir um `RedisStreamEventBus` real, **ignorando** o override de settings que os testes de DLQ fazem (`self.settings(DOCUPARSE_LOCAL_EVENT_DIR=...)`). Isso produzia 4 falhas fantasma em `documents/tests/test_dlq_command.py` que desaparecem assim que `DOCUPARSE_EVENT_BUS` não está no ambiente do processo de teste. Vale considerar trocar `event_bus_from_env` para ler de `django.conf.settings` (que os testes conseguem sobrescrever) em vez de `os.environ` diretamente — hoje isso é uma armadilha silenciosa para qualquer um que rode os testes com o `.env` de dev carregado no shell.

---

## 2. Bugs conhecidos para tratamento futuro

### 2.1 [backend-core] Fluxo de aprovação nunca dispara a integração ERP — 4 testes afetados

**Sintoma**: depois de aprovar um documento validado, `document.status` fica `APPROVED` em vez de `ERP_INTEGRATION_REQUESTED`; nenhum evento é publicado; o export JSON aprovado nunca é gerado.

**Causa raiz**: `documents/services/erp_publisher.py:18` implementa `publish_erp_integration_requested(document, connector)` — cria `ERPIntegrationAttempt`, respeita `approved_export_enabled`, exporta o JSON e transiciona o documento para `ERP_INTEGRATION_REQUESTED` (linha 68). **Mas nada no fluxo de aprovação chama essa função.** Em `documents/views.py:463-465`:
```python
if decision == ValidationDecision.Decision.APPROVED:
    document.transition_to(Document.Status.APPROVED)
```
transiciona direto para `APPROVED` e retorna, sem passar por `erp_publisher`. A função parece órfã — implementada e testada em isolamento, mas nunca conectada à view que decide a aprovação. Provavelmente ficou desconectada durante algum refactor (candidatos: field-versioning `007`, ou o trabalho de multi-tenancy `010`).

**Testes afetados** (`documents/tests/test_api.py`):
- `test_operator_can_approve_document_via_api:311` — espera `ERP_INTEGRATION_REQUESTED`, recebe `APPROVED`.
- `test_approve_document_publishes_erp_integration_requested_and_exports_json:343` — `IndexError` ao ler `events[0]` (nenhum evento publicado).
- `test_approval_respects_disabled_json_export_setting:447` — mesmo `IndexError`.
- `test_approve_document_uses_corrected_fields_for_export:385` — `extraction.fields` fica como `{'valor': {'value': 'R$ 999,99', 'confidence': 1.0}}` (formato interno pós field-versioning) em vez do `{'valor': 'R$ 999,99'}` "achatado" que o export produziria — mais uma consequência de o export nunca rodar.

**Próximo passo sugerido**: decidir com o dono da feature se `erp_publisher.publish_erp_integration_requested` deveria ser chamado a partir de `views.py:464` (dentro do `if decision == APPROVED`) e, se sim, religar; ou se a feature foi descontinuada de propósito, e então remover o código morto (`erp_publisher.py`, `ERPIntegrationAttempt`, os 4 testes) em vez de deixá-lo enganosamente "implementado".

### 2.2 [backend-core] Auto-extração pulada silenciosamente — 2 testes afetados

**Sintoma**: `document.extraction_result` não existe (`RelatedObjectDoesNotExist`) ou mantém dados antigos após reprocessar OCR.

**Causa raiz**: `documents/services/ocr_processor.py:179-182` — `_resolve_schema_for_extraction(document, raw_text)` retorna `None` para o texto simulado usado nos testes, e o código loga `auto_extract_skipped_no_schema` e desiste silenciosamente (sem levantar erro, sem criar `ExtractionResult`).

**Testes afetados**:
- `test_process_ocr_endpoint_updates_extraction_result:203`
- `test_reprocess_ocr_endpoint_replaces_existing_extraction_result:251`

**Próximo passo sugerido**: verificar se `_resolve_schema_for_extraction` deveria casar com algum `SchemaConfig`/`LayoutConfig` que o `setUp` do teste não está criando (fixture desatualizada), ou se é uma regressão real na lógica de resolução de schema (i.e., o comportamento esperado antigo era "sempre cria extraction_result mesmo sem schema" e isso mudou sem atualizar os testes).

### 2.3 [backend-core] Teste referencia função renomeada — 1 teste afetado

**Sintoma**: `AttributeError: <module 'documents.views'> does not have the attribute 'start_document_ocr_thread'`.

**Causa raiz**: `documents/tests/test_api.py:124` faz `patch("documents.views.start_document_ocr_thread")`, mas essa função não existe mais em `documents/views.py`. O disparo automático de OCR hoje é feito por `submit_document_processing(document.id)` (`documents/views.py:297`, dentro de `document_received_event_view`).

**Próximo passo sugerido**: trocar o alvo do `patch` para `documents.views.submit_document_processing` e ajustar as asserções conforme a assinatura atual.

### 2.4 [backend-com] Teste desatualizado em relação a uma resposta nova da API — 1 teste afetado

**Sintoma**: `AssertionError` comparando dict — a resposta real tem uma chave `duplicate_count` a mais.

**Causa raiz**: `api/app.py:243-244` retorna `{"accepted_count": ..., "duplicate_count": ..., "documents": [...]}` (detecção de duplicados foi adicionada à resposta do webhook de e-mail), mas `tests/test_backend_com_app.py:198` ainda faz `assert response.json() == {"accepted_count": 0, "documents": []}` (igualdade exata, sem a chave nova).

**Próximo passo sugerido**: trivial — atualizar a asserção para `{"accepted_count": 0, "duplicate_count": 0, "documents": []}`.

### 2.5 [backend-ocr] `FieldExtractor` não é mais referenciado em `process_document` — 7 testes afetados

**Sintoma**: `AttributeError: <module 'application.process_document'> has no attribute 'FieldExtractor'` ao tentar `monkeypatch.setattr(process_module, "FieldExtractor", ...)`.

**Causa raiz**: `domain/field_extractor.py:43` ainda define `class FieldExtractor`, mas `application/process_document.py` não importa mais `FieldExtractor`/`field_extractor` (conferido — só importa classifier, engine_resolver e as engines de OCR). A extração de campos parece ter sido desacoplada do `process_document` do backend-ocr, possivelmente movida para o `langextract-service` num refactor anterior, deixando os testes presos à API antiga.

**Testes afetados** (`tests/test_process_document_bugs.py:58,78,97,122,146,183` e mais 2 na mesma classe):
- `test_process_document_calls_classifier_with_filename_and_content`
- `test_process_document_skips_semantic_extraction_by_default`
- `test_process_document_runs_legacy_extraction_when_requested`
- `test_process_document_routes_digital_pdf_to_docling`
- `test_process_document_routes_image_pdf_to_openrouter`
- `test_process_document_fallback_does_not_use_undefined_ocr_result`
- `test_openrouter_image_uses_key_values_when_extracted_text_is_empty`

**Próximo passo sugerido**: confirmar com o dono da feature se a extração de campos saiu mesmo do backend-ocr (nesse caso os testes estão testando um contrato morto e devem ser removidos/migrados para o langextract-service) ou se é uma regressão (nesse caso `process_document.py` deveria voltar a chamar `FieldExtractor`).

### 2.6 [backend-ocr] Testes dependem de arquivos de exemplo que não existem neste ambiente — 4 testes afetados

**Sintoma**: `FileNotFoundError` apontando para caminhos como `/docuparser/docs_teste/AnyScanner_12_09_2025.pdf`, `/docuparser/docs_teste/PHOTO-2026-01-08-18-44-00.jpg` e um PDF de condomínio.

**Causa raiz**: esses testes leem arquivos reais de um diretório `docs_teste/` que não está versionado no repo (nem existe neste ambiente) — parecem ter sido escritos e commitados na máquina de um dev específico com uma pasta de amostras local.

**Testes afetados**:
- `tests/test_classifier.py::test_text_pdf_with_more_text_blocks_than_image_blocks_is_digital_pdf`
- `tests/test_real_pdf_ocr.py::test_anyscanner_pdf_runs_with_local_tesseract`
- 2 testes dentro de `tests/test_process_document_bugs.py`

**Próximo passo sugerido**: mover os PDFs/imagens de amostra para um diretório de fixtures versionado no repo (ex.: `backend-ocr/tests/fixtures/`) com arquivos pequenos e sem dados sensíveis, ou marcar esses testes com `@pytest.mark.skipif` quando o diretório não existir, para não quebrar CI/outros devs.

---

## 3. Resumo por severidade

| # | Serviço | Bugs reais de aplicação | Testes desatualizados/fixtures faltando |
|---|---|---|---|
| 2.1 | backend-core | ✅ integração ERP desconectada da view de aprovação | — |
| 2.2 | backend-core | ⚠️ a confirmar (schema resolution) | possivelmente fixture do teste |
| 2.3 | backend-core | — | ✅ teste referencia função renomeada |
| 2.4 | backend-com | — | ✅ asserção desatualizada (chave nova) |
| 2.5 | backend-ocr | ⚠️ a confirmar (FieldExtractor desacoplado) | possivelmente teste de contrato morto |
| 2.6 | backend-ocr | — | ✅ fixtures de arquivo ausentes no repo |

O item **2.1 é o mais sério**: é uma feature de negócio (integração ERP + export de documentos aprovados) que está implementada, tem testes, mas não roda em produção porque a view nunca chama a função.
