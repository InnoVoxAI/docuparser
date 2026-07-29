# Tasks: Workflow de Aprovação e Rejeição de Documentos

**Feature**: [workflow-approval-rejection.md](../specs/workflow-approval-rejection.md)
**Plan**: [implementation-approval-rejection-plan.md](../implementation/implementation-approval-rejection-plan.md)
**Branch**: `002-doc-approval-rejection` | **Date**: 2026-06-03

---

## Format: `[ID] [P?] [US#] Description — file path`

- **[P]**: Paralelizável — arquivo diferente ou seção independente sem dependência de task incompleta
- **[US#]**: User story servida (US1–US5 do spec)
- Caminhos de arquivo relativos à raiz do repositório
- Tasks sem `[US#]` são infra/pré-requisito compartilhado

---

## Phase 1: Database

> **Nenhuma migração necessária.** Os modelos `Document`, `ValidationDecision` e `ExtractionResult`
> já possuem todos os campos necessários. `ValidationDecision.created_at` é usado como fonte de
> `decision_date` via serializer — sem alteração de schema.

---

## Phase 2: Backend Domain

**Goal**: Expor `decision_date` via `DocumentListSerializer` para uso nas telas Aprovados e Rejeitados.

**Done when**: `GET /api/ocr/documents` retorna `decision_date` com valor ISO 8601 para documentos decididos e `null` para os demais.

- [x] T001 [P] [US4] Add `decision_date` SerializerMethodField and `get_decision_date` method to `DocumentListSerializer` — `docuparse-project/backend-core/documents/serializers.py`

---

## Phase 3: Backend API

**Goal**: Adicionar guardas de validação ao `document_validation_view` e configurar prefetch para suportar `decision_date` sem queries N+1.

**Dependencies**: Nenhuma (pode ser desenvolvida em paralelo com Phase 2)

**Done when**: `POST /api/ocr/documents/{id}/validate` retorna 422 quando sem `ExtractionResult`; retorna 400 quando `decision=rejected` e `notes` vazio ou só espaços; `GET /documents` inclui `decision_date` sem N+1 queries.

- [x] T002 Add `select_related('extraction_result')` to queryset in `document_validation_view` — `docuparse-project/backend-core/documents/views.py`
- [x] T003 [US1][US2] Add extraction-complete guard: return HTTP 422 with `{"detail": "Extração de campos não concluída. Execute a extração antes de aprovar ou rejeitar."}` when no `ExtractionResult` exists — `docuparse-project/backend-core/documents/views.py`
- [x] T004 [US2] Add rejection-notes guard: return HTTP 400 with `{"detail": "Motivo da rejeição é obrigatório."}` when `decision == 'rejected'` and `notes.strip()` is empty — `docuparse-project/backend-core/documents/views.py`
- [x] T005 [P] Add `Prefetch` for `validationdecision_set` with `to_attr='_prefetched_decisions'` to `documents_inbox_view` queryset — `docuparse-project/backend-core/documents/views.py`

---

## Phase 4: Frontend — Tela de Validação

**Goal**: Adicionar guardas client-side no `submitDecision` e melhorar feedback visual do campo de motivo de rejeição.

**Dependencies**: T003 (alinhamento de mensagens com as respostas do backend)

**Done when**: Clicar em "Aprovar" ou "Rejeitar" sem pré-condições exibe mensagem de erro inline; nenhuma chamada de API é disparada; campo `notes` exibe borda vermelha ao tentar rejeitar sem preencher.

- [x] T006 [US1][US2] Add guard in `submitDecision`: block and display error "Execute a extração de campos antes de aprovar ou rejeitar." if `selectedDocument.extraction_result` is null — `docuparse-project/frontend/src/main.jsx`
- [x] T007 [US2] Add guard in `submitDecision`: block and display error "O motivo da rejeição é obrigatório." if `decision === 'rejected'` and `notes.trim() === ''` — `docuparse-project/frontend/src/main.jsx`
- [x] T008 [US2] Update notes textarea: set `placeholder` to "Motivo da rejeição (obrigatório para rejeitar)" and add red-border error state when rejection is attempted with empty notes — `docuparse-project/frontend/src/main.jsx`

---

## Phase 5: Navigation / Menu

**Goal**: Adicionar item "Aprovados" ao menu lateral.

**Dependencies**: Nenhuma (alteração isolada no array `NAV_ITEMS`)

**Done when**: Link "Aprovados" aparece no menu lateral entre os itens existentes e navega para a tela correta sem erros de console.

- [x] T009 [US4] Add `{ id: 'approved', label: 'Aprovados', icon: CheckCircle2 }` to `NAV_ITEMS` array — `docuparse-project/frontend/src/main.jsx`

---

## Phase 6: Frontend — Tela de Documentos Aprovados

**Goal**: Criar tela "Aprovados" com tabela de documentos aprovados, status e data de aprovação.

**Dependencies**: T001 (campo `decision_date` disponível na API), T009 (item de navegação criado)

**Done when**: Navegar para "Aprovados" exibe tabela com colunas Documento / Status / Data de Aprovação; estado vazio exibe "Nenhum documento aprovado."; data exibe valor do `decision_date` da API.

- [x] T010 [US4] Add `approvedDocuments` useMemo computed array filtering `d.status === 'APPROVED'` from `documents` state — `docuparse-project/frontend/src/main.jsx`
- [x] T011 [US4] Create `ApprovedView` component: table with columns filename, `<StatusBadge status={document.status} />`, `formatDate(document.decision_date ?? document.updated_at)`, and empty state "Nenhum documento aprovado." — `docuparse-project/frontend/src/main.jsx`
- [x] T012 [US4] Add `activeView === 'approved'` case to render `<ApprovedView documents={approvedDocuments} />` in the main view router — `docuparse-project/frontend/src/main.jsx`

---

## Phase 7: Frontend — Tela de Documentos Rejeitados

**Goal**: Atualizar `RejectedRow` para exibir data exata de rejeição via `decision_date` e adicionar ação "Visualizar Motivo".

**Dependencies**: T001 (campo `decision_date` disponível na API)

**Done when**: Coluna de data em Rejeitados exibe `decision_date` quando disponível; botão "Visualizar Motivo" expande ou abre overlay com o texto completo de `rejection_notes`.

- [x] T013 [US5] Update date display in `RejectedRow` from `formatDate(document.updated_at)` to `formatDate(document.decision_date ?? document.updated_at)` — `docuparse-project/frontend/src/main.jsx`
- [x] T014 [US5] Add "Visualizar Motivo" button to `RejectedRow` with local state `viewingMotivo` (boolean) that expands inline or shows overlay with full `rejection_notes` text — `docuparse-project/frontend/src/main.jsx`

---

## Phase 8: Testing

**Goal**: Cobertura de integração e unitária para todas as guardas e campos novos do backend.

**Dependencies**: T001–T005 (backend completo antes dos testes)

**Done when**: `pytest docuparse-project/backend-core` passa sem erros; todos os cenários de guarda e o campo `decision_date` cobertos.

- [x] T015 [P] [US1] Integration test: approve document with ExtractionResult → expect 201 and `document.status == 'APPROVED'` — `docuparse-project/backend-core/documents/tests/test_validation_view.py`
- [x] T016 [P] [US1] Integration test: approve document without ExtractionResult → expect 422 with detail message — `docuparse-project/backend-core/documents/tests/test_validation_view.py`
- [x] T017 [P] [US2] Integration test: reject document with valid non-empty notes → expect 201 and `ValidationDecision.notes` persisted — `docuparse-project/backend-core/documents/tests/test_validation_view.py`
- [x] T018 [P] [US2] Integration test: reject document with empty string notes → expect 400 with detail message — `docuparse-project/backend-core/documents/tests/test_validation_view.py`
- [x] T019 [P] [US2] Integration test: reject document with whitespace-only notes → expect 400 with detail message — `docuparse-project/backend-core/documents/tests/test_validation_view.py`
- [x] T020 [P] Unit test for `get_decision_date`: returns `null` when no `ValidationDecision` exists; returns `created_at` of the most recent decision when one exists — `docuparse-project/backend-core/documents/tests/test_serializers.py`
- [x] T021 [P] [US4] Integration test: `GET /documents?status=APPROVED` returns only APPROVED docs, each with non-null `decision_date` — `docuparse-project/backend-core/documents/tests/test_documents_inbox_view.py`

---

## Phase 9: QA Validation

**Goal**: Verificação manual do fluxo completo de aprovação, rejeição, navegação e ações em Rejeitados.

**Dependencies**: T001–T014 completos; aplicação rodando localmente (`npm run dev` + `python manage.py runserver`).

**Done when**: Todos os cenários abaixo verificados sem erros de console e comportamento consistente com o spec.

- [ ] T022 [US1][US3] Manual: approve a pending document with extraction complete → verify it disappears from Inbox and appears in Aprovados with correct date
- [ ] T023 [US2][US3] Manual: reject a pending document with a reason → verify it disappears from Inbox and appears in Rejeitados with the correct motivo
- [ ] T024 [US1][US2] Manual: attempt approve/reject on document without extraction → verify inline error message with no API call (network tab shows no request)
- [ ] T025 [US2] Manual: attempt reject without filling motivo field → verify inline error and red border on notes textarea
- [ ] T026 [US4] Manual: navigate to Aprovados from sidebar menu → verify table columns Documento / Status / Data de Aprovação and empty state "Nenhum documento aprovado."
- [ ] T027 [US5] Manual: click "Visualizar Motivo" on rejected document → verify full rejection reason text is displayed (not truncated)
- [ ] T028 [US5] Manual: click "Reprocessar OCR" on rejected document → verify document returns to Inbox as pending after reprocessing completes
- [ ] T029 [US5] Manual: click "Excluir" on rejected document → verify confirmation prompt appears and document is removed from all views after confirmation

---

## Dependency Graph

```
Phase 2 — T001 (serializer decision_date)
  │
  ├──► Phase 6 — T010, T011, T012 (ApprovedView)       [depends on T001]
  └──► Phase 7 — T013, T014       (RejectedRow updates) [depends on T001]

Phase 3 — T002 → T003 → T004 (view guards, sequential within phase)
  │
  └──► Phase 4 — T006, T007, T008 (client-side guards)  [depends on T003]

Phase 3 — T005 (prefetch, parallel with T002–T004)

Phase 5 — T009 (NAV_ITEMS)
  └──► Phase 6 — T010, T011, T012                        [depends on T009]

Phase 8 — T015–T021 (tests)     [depends on T001–T005]
Phase 9 — T022–T029 (QA manual) [depends on T001–T014]
```

## Parallel Opportunities

| Parallel Group | Tasks | Reason |
|----------------|-------|--------|
| Backend ∥ Serializer | T001 ∥ T002–T004 | Different files (`serializers.py` vs `views.py`) |
| View guards ∥ Prefetch | T002–T004 ∥ T005 | Different view functions in `views.py` |
| Frontend tasks | T006–T008 ∥ T009 | Non-overlapping sections of `main.jsx` |
| All integration tests | T015–T021 | Independent test cases, same phase |

## MVP Scope (US1 + US2 — P1 stories)

Minimum increment to demonstrate end-to-end approval/rejection:

- **T001** — `decision_date` no serializer
- **T002, T003, T004** — guardas de backend
- **T006, T007** — guardas de frontend
- **T009, T010, T011, T012** — tela Aprovados acessível

Entrega: operador pode aprovar e rejeitar documentos com restrições funcionando; tela Aprovados acessível.
