---

description: "Task list for Edição e Versionamento de Campos Extraídos"
---

# Tasks: Edição e Versionamento de Campos Extraídos

**Input**: Design documents from `docs/specs/007-extracted-field-versioning/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/field-versions-api.md, quickstart.md

**Tests**: INCLUÍDOS — a Constituição (Princípio II) exige testes unitários e de integração para handlers de API, lógica de negócio e contratos entre serviços. Tasks de teste são escritas antes da implementação correspondente.

**Organization**: Tasks agrupadas por user story (US1–US4) para implementação e teste independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: User story (US1–US4) — apenas nas fases de story

## Path Conventions

Web app multi-serviço. Backend em `docuparse-project/backend-core/documents/`; frontend em `docuparse-project/frontend/src/main.jsx`. Caminhos abaixo são relativos à raiz do repositório.

⚠️ **Conflitos de arquivo conhecidos** (impedem paralelismo entre stories):
- `documents/views.py` é tocado por US1, US3, US4 → sequencial.
- `documents/urls.py` é tocado por US1, US3 → sequencial.
- `frontend/src/main.jsx` é tocado por US1, US2, US3 → sequencial.
- `documents/tests/test_field_versions_api.py` é tocado por várias stories → sequencial entre elas.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Criar os arquivos novos vazios para destravar implementação e testes.

- [X] T001 [P] Criar módulo de serviço (skeleton com assinaturas + type hints) em `docuparse-project/backend-core/documents/services/field_versioning.py`
- [X] T002 [P] Criar arquivos de teste vazios `docuparse-project/backend-core/documents/tests/test_field_versioning.py` e `docuparse-project/backend-core/documents/tests/test_field_versions_api.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelo, migração, serviço base e serializer dos quais TODAS as user stories dependem.

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase.

- [X] T003 Adicionar modelo `ExtractionFieldVersion` (com `SourceType` TextChoices, FK `document`/`previous_version`/`created_by`, `version_number`, `fields` JSON, `confidence`, `is_active`, constraints `unique_field_version_per_document` e `unique_active_field_version_per_document` parcial, índices) em `docuparse-project/backend-core/documents/models.py` (data-model.md)
- [X] T004 Gerar migration de schema para `ExtractionFieldVersion` em `docuparse-project/backend-core/documents/migrations/` (`makemigrations documents`)
- [X] T005 Adicionar data migration de backfill: criar versão inicial (`version_number=1`, `INITIAL_EXTRACTION`, `is_active=True`, `previous_version=null`) para cada `ExtractionResult` existente, em `docuparse-project/backend-core/documents/migrations/` (research.md D8)
- [X] T006 Implementar núcleo do serviço em `docuparse-project/backend-core/documents/services/field_versioning.py`: `get_active_version(document)`, `create_version(document, fields, source_type, created_by=None, previous_version auto)` com transação atômica (desativar ativa anterior, calcular `version_number`, ativar nova) e sincronização de `ExtractionResult.fields/confidence` com a versão ativa (data-model.md, FR-013/FR-014/FR-015/FR-016/FR-023)
- [X] T007 [P] Implementar `ExtractionFieldVersionSerializer` (expondo `version_number`, `source_type`, `is_active`, `previous_version_number`, `created_at`, `created_by`, `fields`) em `docuparse-project/backend-core/documents/serializers.py` (contracts/field-versions-api.md)

**Checkpoint**: Fundação pronta — versionamento básico funciona e versões podem ser criadas/lidas programaticamente.

---

## Phase 3: User Story 1 - Editar e Salvar Campos Extraídos (Priority: P1) 🎯 MVP

**Goal**: Usuário edita o valor de campos e salva com confirmação, criando uma nova versão ativa `MANUAL_EDIT`; campos editados ficam com confiança 100%; conflito de versão é bloqueado.

**Independent Test**: Editar o valor de um campo, clicar "Salvar Alterações", confirmar → nova versão ativa criada com o valor corrigido (confiança 100%), versão anterior preservada; cancelar não persiste; `base_version` obsoleta retorna 409.

### Tests for User Story 1 ⚠️ (escrever e ver FALHAR antes da implementação)

- [X] T008 [P] [US1] Testes unitários do serviço: criação de versão `MANUAL_EDIT`; confiança 100% em campo alterado e confiança preservada em campo inalterado (FR-025); conflito quando `base_version` não é a ativa (FR-024, sem criar versão); rejeição de lista vazia e de salvamento sem alterações (Edge Cases), em `docuparse-project/backend-core/documents/tests/test_field_versioning.py`
- [X] T009 [P] [US1] Testes de integração do endpoint `PUT /documents/{id}/fields`: 201 (nova versão ativa + `ExtractionResult` sincronizado), 409 (conflito), 422 (lista vazia/sem alteração), 403 (sem permissão `documents.validate`), em `docuparse-project/backend-core/documents/tests/test_field_versions_api.py`

### Implementation for User Story 1

- [X] T010 [US1] Estender `field_versioning.py`: regra de confiança 100% para campos alterados (FR-025) e checagem de concorrência otimista via `base_version_number` (FR-024) em `docuparse-project/backend-core/documents/services/field_versioning.py` (depende de T006)
- [X] T011 [US1] Implementar `document_save_fields_view` (PUT, `@require_permission("documents.validate")`, envelope de resposta, mensagens acionáveis, 201/409/422) em `docuparse-project/backend-core/documents/views.py` (contracts/field-versions-api.md §1)
- [X] T012 [US1] Registrar rota `documents/<uuid:document_id>/fields` → `document_save_fields_view` em `docuparse-project/backend-core/documents/urls.py`
- [X] T013 [US1] Frontend: adicionar botão "Salvar Alterações" abaixo da lista no `LangExtractPanel`/`ValidationView`, com diálogo de confirmação (FR-007), chamada `PUT /documents/{id}/fields` (enviando `base_version_number` + `fields`), estados loading/sucesso/erro e tratamento de 409 (aviso + recarregar versão ativa), em `docuparse-project/frontend/src/main.jsx`

**Checkpoint**: US1 totalmente funcional — fluxo de editar + salvar com versionamento entregue (MVP).

---

## Phase 4: User Story 2 - Remover Campos da Lista (Priority: P1)

**Goal**: Usuário remove campos da lista ativa; ao salvar, nova versão ativa não contém os campos removidos, e a versão anterior os preserva.

**Independent Test**: Remover um campo, salvar e confirmar → nova versão ativa sem o campo; histórico mostra a versão anterior ainda com o campo.

### Tests for User Story 2 ⚠️

- [X] T014 [US2] Teste de integração: salvar com um campo removido cria versão ativa sem ele e mantém o campo na versão anterior (FR-013), em `docuparse-project/backend-core/documents/tests/test_field_versions_api.py`

### Implementation for User Story 2

- [X] T015 [US2] Frontend: garantir que a ação "Remover" marca estado não salvo e que campos removidos são excluídos do payload de "Salvar Alterações" (reuso do endpoint da US1; sem nova rota backend), em `docuparse-project/frontend/src/main.jsx` (depende de T013)

**Checkpoint**: US1 e US2 funcionam de forma independente sobre o mesmo endpoint de salvamento.

---

## Phase 5: User Story 3 - Consultar Histórico de Versões (Priority: P2)

**Goal**: Usuário visualiza todas as versões (ativa + anteriores), identificáveis, com campos/valores/confiança, somente leitura.

**Independent Test**: Em documento com múltiplas versões, acionar "Visualizar Histórico" → lista desc por `version_number`, cada versão com metadados e campos; nenhuma ação de edição/remoção disponível.

### Tests for User Story 3 ⚠️

- [X] T016 [US3] Teste de integração `GET /documents/{id}/field-versions`: todas as versões ordenadas desc, `meta.count`/`meta.active_version_number`, estado vazio sem erro, somente leitura (FR-019–FR-022), em `docuparse-project/backend-core/documents/tests/test_field_versions_api.py`

### Implementation for User Story 3

- [X] T017 [US3] Implementar `document_field_versions_view` (GET, `@require_permission("documents.validate")`, usa `ExtractionFieldVersionSerializer`, envelope com `meta`) em `docuparse-project/backend-core/documents/views.py` (contracts/field-versions-api.md §2)
- [X] T018 [US3] Registrar rota `documents/<uuid:document_id>/field-versions` → `document_field_versions_view` em `docuparse-project/backend-core/documents/urls.py`
- [X] T019 [US3] Frontend: adicionar ação "Visualizar Histórico" e modal/painel somente leitura listando versões (número, tipo, data, autor) e seus campos/valores/confiança, em `docuparse-project/frontend/src/main.jsx` (depende de T013)

**Checkpoint**: Histórico consultável e somente leitura, sobre as versões criadas por US1/US2/US4.

---

## Phase 6: User Story 4 - Versionamento Automático por Processamento (Priority: P2)

**Goal**: Extração/processamento/reprocessamento criam versões automaticamente (sem sobrescrever), com o tipo de origem correto, tornando-se ativas.

**Independent Test**: Reprocessar documento já versionado → nova versão `REPROCESSING` ativa; versões anteriores intactas; primeira extração registra `INITIAL_EXTRACTION`.

### Tests for User Story 4 ⚠️

- [X] T020 [US4] Testes de integração: `POST /langextract` cria `INITIAL_EXTRACTION` na primeira vez e `REPROCESSING` nas seguintes (sem sobrescrever — FR-013); `POST /validate` com `corrected_fields` cria versão `MANUAL_EDIT` em vez de sobrescrever; preserva versões anteriores (FR-016), em `docuparse-project/backend-core/documents/tests/test_field_versions_api.py`

### Implementation for User Story 4

- [X] T021 [US4] Alterar `document_langextract_view`: substituir `ExtractionResult.objects.update_or_create(...)` por chamada ao serviço de versionamento (`INITIAL_EXTRACTION` se não houver versão, senão `REPROCESSING`); manter shape de resposta atual, em `docuparse-project/backend-core/documents/views.py` (depende de T006)
- [X] T022 [US4] Alterar `document_validation_view`: remover sobrescrita direta de `extraction_result.fields`; quando `corrected_fields` presente e diferente da ativa, criar versão `MANUAL_EDIT` via serviço antes de registrar a `ValidationDecision`, em `docuparse-project/backend-core/documents/views.py` (depende de T006)

**Checkpoint**: Todos os gatilhos de versão (FR-011) cobertos; nenhuma sobrescrita remanescente.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T023 [P] Rodar ruff em `docuparse-project/backend-core/documents/` e corrigir violações (Princípio I) — **não executado**: ruff não está instalado neste ambiente. `python manage.py check` passou sem issues; código segue o estilo existente (type hints, funções curtas).
- [ ] T024 [P] Rodar ESLint em `docuparse-project/frontend/` e corrigir violações (Princípio I) — **não executado**: projeto não tem config ESLint e o build Vite está quebrado neste ambiente (Node v24 vs Vite). JSX validado via `@babel/parser` (parse OK).
- [X] T025 [P] Verificar cobertura ≥ 80% nos arquivos tocados do `documents` (Princípio II) — `field_versioning.py` em **89%**.
- [ ] T026 Executar o roteiro de validação manual dos 5 fluxos em `docs/specs/007-extracted-field-versioning/quickstart.md` — **pendente**: requer o stack Docker + frontend em execução (indisponível neste ambiente). Os 5 fluxos têm cobertura equivalente nos testes automatizados de backend.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as user stories.
- **User Stories (Phase 3–6)**: dependem da Foundational. Ordem de prioridade: US1 (P1) → US2 (P1) → US3 (P2) → US4 (P2).
- **Polish (Phase 7)**: depende das stories desejadas concluídas.

### User Story Dependencies

- **US1 (P1)**: depende apenas da Foundational. Entrega o endpoint de salvamento (base para US2).
- **US2 (P1)**: reusa o endpoint da US1; depende de T013 (frontend de salvamento). Backend já coberto.
- **US3 (P2)**: depende da Foundational (serializer/modelo); frontend depende de T013. Independente de US1/US2 no backend.
- **US4 (P2)**: depende da Foundational (serviço); independente de US1–US3 (altera outros endpoints).

### Conflitos de arquivo (sequencialidade obrigatória)

- `views.py`: T011 (US1) → T017 (US3) → T021/T022 (US4).
- `urls.py`: T012 (US1) → T018 (US3).
- `main.jsx`: T013 (US1) → T015 (US2) → T019 (US3).
- `test_field_versions_api.py`: T009 → T014 → T016 → T020.

### Within Each User Story

- Testes escritos e falhando antes da implementação.
- Modelo/serviço antes de endpoints; endpoints antes do frontend.

### Parallel Opportunities

- Setup: T001 e T002 em paralelo.
- Foundational: T007 [P] paralelo a T003–T006 (arquivo diferente — `serializers.py`); T003→T004→T005 são sequenciais (mesmo domínio de migração); T006 depende de T003.
- US1: T008 [P] (test_field_versioning.py) e T009 [P] (test_field_versions_api.py) em paralelo.
- Polish: T023, T024, T025 em paralelo.
- US4 é independente de US3 no backend, mas ambos tocam `views.py` → não paralelizar.

---

## Parallel Example: User Story 1

```bash
# Testes da US1 (arquivos diferentes) juntos:
Task: "Testes unitários do serviço em documents/tests/test_field_versioning.py"
Task: "Testes de integração do PUT /fields em documents/tests/test_field_versions_api.py"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: Setup.
2. Phase 2: Foundational (CRÍTICO — bloqueia tudo).
3. Phase 3: US1 (editar + salvar com versão).
4. **PARAR e VALIDAR**: testar US1 isoladamente.
5. Demo do MVP.

### Incremental Delivery

1. Setup + Foundational → fundação pronta.
2. US1 → testar → demo (MVP: editar e salvar versionado).
3. US2 → testar → demo (remover campos).
4. US3 → testar → demo (histórico somente leitura).
5. US4 → testar → demo (versionamento automático em extração/reprocessamento).

---

## Notes

- [P] = arquivos diferentes, sem dependência pendente.
- Verificar que os testes falham antes de implementar.
- Commit após cada task ou grupo lógico.
- Toda query filtra por tenant; respostas no envelope `{ data, error, meta }`; mensagens de erro humanas/acionáveis (Constituição III).
- Imutabilidade: nenhuma task expõe edição/exclusão de versão existente (FR-013/FR-016/FR-021).
