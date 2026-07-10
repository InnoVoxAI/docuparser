---
description: "Task list for feature 011 — Armazenamento de objetos compartilhado entre backends"
---

# Tasks: Armazenamento de objetos compartilhado entre backends

**Input**: Design documents from `docs/specs/011-shared-object-storage/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Incluídos — a Constituição (Testing Standards) exige testes unitários, de contrato inter-serviço e de regressão para esta classe de mudança.

**Organization**: Tarefas agrupadas por user story (prioridade da spec) para implementação e teste independentes. Caminhos são relativos à raiz do repositório; o código-fonte vive sob `docuparse-project/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: US1, US2, US3, US4 (mapeia as user stories da spec)

## Path Conventions

- Pacote compartilhado: `docuparse-project/shared/docuparse_storage/`
- Serviços: `docuparse-project/{backend-com,backend-core,backend-ocr,layout-service,langextract-service}/`
- Testes: junto de cada serviço/pacote (`.../tests/`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependências e ambiente de teste para o storage S3/MinIO

- [x] T001 Adicionar `boto3` como dependência (import lazy) aos serviços de I/O em `docuparse-project/backend-com/pyproject.toml`, `docuparse-project/backend-ocr/pyproject.toml`, `docuparse-project/layout-service/pyproject.toml`, `docuparse-project/langextract-service/pyproject.toml` e `docuparse-project/backend-core/requirements.txt`
- [x] T002 [P] Adicionar `moto` (mock S3, sem rede/disco — exigência da Constituição) às dependências de teste do pacote compartilhado e serviços em `docuparse-project/shared/` e nos `pyproject.toml`/requirements de teste
- [x] T003 [P] Prover MinIO para testes de integração (serviço em compose ou fixture) e documentar o alvo em `docs/specs/011-shared-object-storage/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Refatorar o pacote `docuparse_storage` em módulos **sem mudança de comportamento**. Bloqueia todas as user stories.

**⚠️ CRITICAL**: Nenhuma user story pode começar até esta fase terminar.

- [x] T004 Extrair `StoredObject` e os helpers de key (`document_original_key`, `document_ocr_raw_text_key`) para `docuparse-project/shared/docuparse_storage/keys.py`
- [x] T005 [P] Definir o `Storage` Protocol (`put_bytes`/`get_bytes`/`delete`) em `docuparse-project/shared/docuparse_storage/base.py` conforme `contracts/storage-interface.md`
- [x] T006 Mover `LocalStorage` (comportamento inalterado, incluindo `_validate_key`) para `docuparse-project/shared/docuparse_storage/local.py`
- [x] T007 Reexportar todos os símbolos em `docuparse-project/shared/docuparse_storage/__init__.py` para preservar os imports existentes (`from docuparse_storage import LocalStorage, document_original_key, ...`)
- [x] T008 Unificar a key do raw_text: substituir o `raw_text_key()` local pelo `document_ocr_raw_text_key` compartilhado em `docuparse-project/backend-ocr/application/ocr_event_worker.py` (mesmo valor; evita drift)

**Checkpoint**: Pacote refatorado, imports intactos, testes atuais passando sem mudança de comportamento.

---

## Phase 3: User Story 1 - Artefato legível entre serviços/pods (Priority: P1) 🎯 MVP

**Goal**: Um artefato gravado por um serviço é recuperável por qualquer outro serviço em pod distinto, via storage S3/MinIO.

**Independent Test**: Gravar um artefato por um serviço e recuperá-lo por outro (bytes idênticos); servir `/documents/{id}/file` a partir de um "pod" diferente do que gravou.

### Tests for User Story 1 ⚠️

- [x] T009 [P] [US1] Teste unitário de `S3Storage` (roundtrip put→get, bytes idênticos, forma de `StoredObject`) com `moto` em `docuparse-project/shared/tests/test_s3_storage.py`
- [x] T010 [P] [US1] Teste de integração cross-serviço (grava via um storage, lê via outro) e serve `/documents/{id}/file` de um pod distinto contra MinIO em `docuparse-project/backend-core/documents/tests/test_storage_cross_service.py`

### Implementation for User Story 1

- [x] T011 [US1] Implementar `S3Storage` (`put_bytes`/`get_bytes`/`delete` no caminho feliz; `StoredObject` com `uri=s3://<bucket>/<key>`, `sha256`, `size_bytes`; boto3 lazy import) em `docuparse-project/shared/docuparse_storage/s3.py`
- [x] T012 [US1] Implementar `RoutingStorage` (escrita → backend configurado; leitura → dispatch pelo esquema da URI) em `docuparse-project/shared/docuparse_storage/routing.py`
- [x] T013 [US1] Implementar a fábrica `get_storage()` (default `local`, lê env) e reexportá-la no `__init__` em `docuparse-project/shared/docuparse_storage/factory.py`
- [x] T014 [P] [US1] Trocar a escrita do arquivo original para `get_storage()` em `docuparse-project/backend-com/src/backend_com/services/document_ingest.py`
- [x] T015 [P] [US1] Trocar as leituras (servir `/file` e leitura do langextract) para `get_storage()` em `docuparse-project/backend-core/documents/views.py`
- [x] T016 [P] [US1] Trocar a leitura do `raw_text.json` para `get_storage()` em `docuparse-project/backend-core/documents/serializers.py`
- [x] T017 [P] [US1] Trocar leitura/escrita para `get_storage()` em `docuparse-project/backend-core/documents/services/ocr_processor.py`
- [x] T018 [P] [US1] Ligar o bootstrap do worker a `get_storage()` em `docuparse-project/backend-ocr/application/ocr_event_worker.py`
- [x] T019 [P] [US1] Ligar o bootstrap do worker a `get_storage()` em `docuparse-project/layout-service/application/layout_event_worker.py`
- [x] T020 [P] [US1] Ligar o bootstrap do worker a `get_storage()` em `docuparse-project/langextract-service/application/extraction_event_worker.py`
- [x] T021 [US1] Corrigir órfão: substituir o path cru (`removeprefix("local://")` + `Path`) por `get_storage().get_bytes(request.raw_text_uri)` em `docuparse-project/layout-service/api/app.py`

**Checkpoint**: Com `DOCUPARSE_STORAGE_BACKEND=s3`, upload em um serviço é lido/servido por outro pod. MVP funcional. (SC-001, SC-002, SC-003)

---

## Phase 4: User Story 2 - Seleção por ambiente, sem regressão (Priority: P1)

**Goal**: Backend selecionável por env com default `local` idêntico ao atual; storage compartilhado ativado explicitamente por ambiente.

**Independent Test**: Sem env, comportamento idêntico ao atual; com `DOCUPARSE_STORAGE_BACKEND=s3`, todos os serviços passam a usar o storage compartilhado — sem alteração de código entre os modos.

### Tests for User Story 2 ⚠️

- [x] T022 [P] [US2] Teste de paridade do default (sem env → comportamento de `LocalStorage`) e de ativação `s3`, incluindo falha explícita quando `s3` sem `S3_BUCKET`/credenciais, em `docuparse-project/shared/tests/test_get_storage_config.py`

### Implementation for User Story 2

- [x] T023 [P] [US2] Expor as envs de storage (`DOCUPARSE_STORAGE_BACKEND`, `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_REGION`, `AWS_*`) em `docuparse-project/backend-com/src/backend_com/config.py` conforme `contracts/storage-config.md`
- [x] T024 [P] [US2] Expor as envs de storage em `docuparse-project/backend-core/core/settings.py`
- [x] T025 [US2] Validação de config em `get_storage()`: backend `s3` sem `S3_BUCKET`/credenciais deve falhar de forma explícita (nunca cair silenciosamente em `local`) em `docuparse-project/shared/docuparse_storage/factory.py`
- [x] T026 [US2] Garantir import lazy de `boto3` (só quando backend efetivo = `s3`) em `docuparse-project/shared/docuparse_storage/factory.py` e `docuparse-project/shared/docuparse_storage/s3.py`

**Checkpoint**: Deploy do código no default não muda comportamento; flip por env liga o storage compartilhado; rollback por env. (SC-007, FR-002, FR-003, FR-008)

---

## Phase 5: User Story 4 - Falha de storage sempre explícita (Priority: P1)

**Goal**: Toda falha de storage produz erro explícito e propagado; nunca um documento persistido sem o arquivo.

**Independent Test**: Simular indisponibilidade/credencial inválida na gravação e confirmar erro observável, sem `Document` criado sem arquivo; objeto inexistente → "não encontrado" distinguível.

### Tests for User Story 4 ⚠️

- [x] T027 [P] [US4] Testes de erro: `NoSuchKey`/404 → `FileNotFoundError`; conexão/credencial inválida propaga exceção distinta; falha de `put` não persiste `Document` — em `docuparse-project/shared/tests/test_s3_storage_errors.py` e `docuparse-project/backend-com/tests/test_ingest_storage_failure.py`

### Implementation for User Story 4

- [x] T028 [US4] Mapear erros em `S3Storage.get_bytes` (`NoSuchKey`/`ClientError(404)` → `FileNotFoundError`; demais `ClientError`/endpoint/credencial propagam) e configurar timeout/retry do client em `docuparse-project/shared/docuparse_storage/s3.py`
- [x] T029 [US4] Auditar caminhos de escrita para que uma falha de `put_bytes` aborte antes de persistir o `Document` (sem sucesso silencioso) em `docuparse-project/backend-com/src/backend_com/services/document_ingest.py` e `docuparse-project/backend-core/documents/services/ocr_processor.py`

**Checkpoint**: Falhas observáveis; zero "documento fantasma". (SC-005, FR-006, FR-007)

---

## Phase 6: User Story 3 - Coexistência de legado e migração sem downtime (Priority: P2)

**Goal**: Referências `local://` legadas continuam legíveis com o novo storage ativo; migração incremental sem downtime; rollback sem perda de acesso.

**Independent Test**: Com `s3` ativo, abrir documento cuja referência é `local://` (legada) e confirmar que abre; migrar e confirmar que continua acessível, sem indisponibilidade.

### Tests for User Story 3 ⚠️

- [x] T030 [P] [US3] Teste de coexistência: `local://` legado legível com backend `s3`; dispatch do `RoutingStorage` para `local://`, `s3://` e key nua — em `docuparse-project/shared/tests/test_routing_coexistence.py`
- [x] T031 [P] [US3] Teste de idempotência/retomada do script de migração (dry-run + apply) em `docuparse-project/scripts/tests/test_migrate_storage.py`

### Implementation for User Story 3

- [x] T032 [US3] Implementar script de migração idempotente (lê `local://` do disco, `put` no S3, atualiza `file_uri`/`raw_text_uri` no DB para `s3://`; retomável) em `docuparse-project/scripts/migrate_storage_local_to_s3.py`
- [x] T033 [US3] Validar/registrar procedimento de rollback (flip para `local` mantendo credenciais S3 para ler já migrados) em `docs/specs/011-shared-object-storage/quickstart.md`

**Checkpoint**: Legado acessível, migração sem downtime, rollback seguro. (SC-006, SC-008, FR-004, FR-005)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Consolidação, cobertura e validação final

- [x] T034 [P] Parametrizar os testes de storage existentes para `local` + `s3(moto)` em `docuparse-project/shared/tests/test_storage_and_events.py`
- [x] T035 [P] Fixar versão de `boto3` e atualizar locks (`uv.lock` / requirements) dos serviços afetados
- [x] T036 [P] Atualizar `docuparse-project/shared/README.md` e `docs/specs/011-shared-object-storage/quickstart.md` com as envs finais
- [x] T037 [P] Adicionar logging estruturado de seleção de backend e de falhas de storage em `docuparse-project/shared/docuparse_storage/factory.py` e `docuparse-project/shared/docuparse_storage/s3.py`
- [x] T038 Executar a validação end-to-end do `quickstart.md` (documento de 20 MB, serve cross-pod, pipeline completo) — SC-004

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende do Setup — **BLOQUEIA todas as user stories**
- **US1 (Phase 3, P1)**: depende do Foundational — entrega o mecanismo (MVP)
- **US2 (Phase 4, P1)**: depende do Foundational; usa `get_storage()`/`factory.py` de US1 (T013) — sequenciar após US1 ou coordenar `factory.py`
- **US4 (Phase 5, P1)**: depende do Foundational; estende `s3.py` de US1 (T011) — sequenciar após US1 ou coordenar `s3.py`
- **US3 (Phase 6, P2)**: depende do Foundational e de US1 (RoutingStorage/get_storage) para a coexistência
- **Polish (Phase 7)**: depende das user stories desejadas concluídas

### Notas de acoplamento por arquivo (evitar conflito)

- `factory.py`: criado em T013 (US1), estendido em T025/T026 (US2) e T037 (Polish) — mesma origem; aplicar em ordem.
- `s3.py`: criado em T011 (US1), estendido em T028 (US4) e T037 (Polish) — mesma origem; aplicar em ordem.
- `views.py` (core): todas as leituras cobertas por T015 (uma tarefa por arquivo).
- `document_ingest.py` e `ocr_processor.py`: wiring em US1 (T014/T017) e auditoria de falha em US4 (T029) — sequenciar.

### Within Each User Story

- Testes escritos e **falhando** antes da implementação (Regression/TDD — Constituição).
- Interface/keys (Foundational) antes das implementações concretas.
- `S3Storage`/`RoutingStorage`/`get_storage()` antes do wiring dos serviços.

### Parallel Opportunities

- Setup: T002, T003 em paralelo.
- Foundational: T005 em paralelo com T004 (arquivos diferentes); T006/T007 sequenciais (dependem de keys).
- US1 wiring: T014–T020 em paralelo (**arquivos de serviços distintos**), após T011–T013.
- US2 config: T023, T024 em paralelo (arquivos distintos).
- US3: T030, T031 em paralelo.
- Polish: T034–T037 em paralelo; T038 por último.

---

## Parallel Example: User Story 1 (wiring dos serviços)

```bash
# Após S3Storage + RoutingStorage + get_storage() (T011–T013), o wiring é paralelo:
Task: "T014 [US1] get_storage() em backend-com/.../document_ingest.py"
Task: "T015 [US1] get_storage() em backend-core/documents/views.py"
Task: "T016 [US1] get_storage() em backend-core/documents/serializers.py"
Task: "T017 [US1] get_storage() em backend-core/documents/services/ocr_processor.py"
Task: "T018 [US1] wiring em backend-ocr/.../ocr_event_worker.py"
Task: "T019 [US1] wiring em layout-service/.../layout_event_worker.py"
Task: "T020 [US1] wiring em langextract-service/.../extraction_event_worker.py"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: Setup
2. Phase 2: Foundational (CRÍTICO — bloqueia tudo)
3. Phase 3: US1 — mecanismo de storage compartilhado
4. **PARAR e VALIDAR**: gravar em um serviço, ler/servir de outro pod (SC-001/002/003)
5. Deploy/demo com `DOCUPARSE_STORAGE_BACKEND=s3` em staging

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → teste cross-pod → deploy (MVP)
3. US2 → paridade no default + rollout seguro por env
4. US4 → falhas explícitas (integridade)
5. US3 → coexistência + migração sem downtime dos dados legados

### Parallel Team Strategy

Após o Foundational, US1 é pré-requisito do restante (fornece `get_storage`/`S3Storage`/`RoutingStorage`). Depois de US1, US2/US4 podem seguir em paralelo (coordenando `factory.py`/`s3.py`), e US3 em seguida.

---

## Notes

- `[P]` = arquivos diferentes, sem dependência pendente.
- Rótulo `[Story]` mapeia a tarefa à user story para rastreabilidade.
- Verificar que os testes falham antes de implementar.
- Fora de escopo (não criar tarefas): bug de rede com→core ("não aparece na listagem") e migração do `approved_exporter` (export ERP) — ver research.md C-04.
- Sem migração de schema no DB (URIs cabem em `CharField(1024)`).
