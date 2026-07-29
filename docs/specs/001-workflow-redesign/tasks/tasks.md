# Tasks: Workflow Redesign – Validação de Documentos

**Branch**: `001-workflow-redesign` | **Date**: 2026-06-02
**Input**: [Implementation Plan](implementation/implementation-workflow-redesign-plan.md) · [Spec](workflow-redesign.md)

**Prerequisites**: Implementation plan complete. All NEEDS CLARIFICATION resolved. Constitution gates passed.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared state dependencies)
- **[Story]**: User story this task belongs to (US1, US2, US3)
- Tasks within the same file (`main.jsx`) must be executed sequentially

---

## Phase 1: Setup

**Purpose**: Confirm icon availability before making changes to the single-file SPA

- [x] T001 Confirm `XCircle` and `RefreshCw` are available in `lucide-react` imports (or add them) in `docuparse-project/frontend/src/main.jsx`

---

## Phase 2: Foundational (Backend Prerequisites)

**Purpose**: Expose `rejection_notes` from the API — required by US3 but does not block US1 or US2

**⚠️ CRITICAL**: Deploy backend changes (or restart the local container) before validating US3 end-to-end

- [x] T002 [P] Add `rejection_notes` `SerializerMethodField` and `get_rejection_notes` method to `DocumentListSerializer`; add `"rejection_notes"` to `Meta.fields` in `docuparse-project/backend-core/documents/serializers.py`
- [x] T003 [P] Add `prefetch_related(Prefetch("validation_decisions", queryset=ValidationDecision.objects.filter(decision="rejected").order_by("-created_at"), to_attr="_prefetched_rejection_decisions"))` to the queryset in `documents_inbox_view` in `docuparse-project/backend-core/documents/views.py`
- [x] T004 [P] Write `test_rejection_notes_in_document_list` regression test asserting `rejection_notes` is returned for a rejected document and is `null` when none exists in `docuparse-project/backend-core/documents/tests/test_api.py`

**Checkpoint**: `GET /api/ocr/documents` response now includes `rejection_notes` field; test passes

---

## Phase 3: User Story 1 – Inbox e Navegação para Validação (Priority: P1) 🎯 MVP

**Goal**: Inbox shows only pending documents; Upload button appears above the list; clicking a document navigates directly to Validation with that document pre-selected.

**Independent Test**: Open Inbox — verify only pending docs appear, Upload button is above the list, clicking a doc opens Validation with that doc loaded. See `docs/specs/quickstart.md` §US1.

- [x] T005 [US1] Add `navigateToValidation(documentId)` handler to `App` that calls `setSelectedDocumentId(documentId)` then `setActiveView('validation')` in `docuparse-project/frontend/src/main.jsx`
- [x] T006 [US1] Update `App` Inbox render call: pass `documents={pendingDocuments}`, `onNavigateToValidation={navigateToValidation}`, and `onNavigateToUpload={() => setActiveView('upload')}` — replace previous `documents` and `onSelectDocument` props in `docuparse-project/frontend/src/main.jsx`
- [x] T007 [US1] Refactor `InboxView` function signature to `({ documents, onNavigateToValidation, onNavigateToUpload })` — remove `selectedDocumentId` and old `onSelectDocument` params in `docuparse-project/frontend/src/main.jsx`
- [x] T008 [US1] Add "Enviar Documento" `<button>` with `<Upload size={16} aria-hidden="true" />` icon above the document list section in `InboxView`, calling `onNavigateToUpload` on click in `docuparse-project/frontend/src/main.jsx`
- [x] T009 [US1] Wire `DocumentTable`'s `onSelectDocument` prop to `onNavigateToValidation` inside `InboxView` in `docuparse-project/frontend/src/main.jsx`

**Checkpoint**: Inbox shows only pending documents; Upload button visible above list; clicking a document navigates to Validation

---

## Phase 4: User Story 2 – Tela de Validação com Metadados (Priority: P2)

**Goal**: Validation screen shows only the selected document (no lateral document queue), displays extracted metadata with empty fields hidden, and blocks direct access without a prior Inbox selection.

**Independent Test**: Navigate from Inbox to Validation — verify no lateral list, non-empty metadata fields appear, empty fields are absent. Access Validation directly via sidebar — verify empty state with redirect. See `docs/specs/quickstart.md` §US2.

- [x] T010 [US2] Remove the lateral "Fila de validação" `<section>` column (first column of 3-column grid) from `ValidationView`, including `validationSearch`, `bulkSelectedIds`, `bulkProgress` state and `filteredValidationDocs`, `bulkDelete`, `bulkReprocess` functions in `docuparse-project/frontend/src/main.jsx`
- [x] T011 [US2] Add `!selectedDocumentId` guard at the top of `ValidationView` body: render empty state with `<ClipboardCheck size={40} aria-hidden="true" />`, message "Selecione um documento no Inbox para iniciar a validacao.", and a button "Ir para o Inbox" that calls `onBackToInbox` in `docuparse-project/frontend/src/main.jsx`
- [x] T012 [US2] Add `onBackToInbox` prop to `ValidationView` signature; update `App` render call to pass `onBackToInbox={() => setActiveView('inbox')}` and remove `documents`, `selectedDocumentId`, `onSelectDocument` props; change grid layout to 2-column `xl:grid-cols-[minmax(360px,0.9fr)_minmax(460px,1.1fr)]` in `docuparse-project/frontend/src/main.jsx`

**Checkpoint**: Validation shows single document with non-empty metadata; direct sidebar access redirects to Inbox

---

## Phase 5: User Story 3 – Lista de Rejeitados (Priority: P3)

**Goal**: A new "Rejeitados" screen lists rejected documents with their rejection reasons; users can reprocess (returns document to Inbox) or permanently delete.

**Independent Test**: Reject a document from Validation, navigate to Rejeitados — verify document appears with rejection reason. Click Reprocessar — verify document reappears in Inbox. Delete a rejected document — verify removal. See `docs/specs/quickstart.md` §US3.

- [x] T013 [US3] Add `{ id: 'rejected', label: 'Rejeitados', icon: XCircle }` to `NAV_ITEMS` between Upload and Validacao; add `rejectedDocuments` useMemo `documents.filter(d => d.status === 'REJECTED')` to `App` in `docuparse-project/frontend/src/main.jsx`
- [x] T014 [US3] Create `RejectedView({ documents, onReprocess, onDelete, onRefresh })` component: header "Documentos rejeitados" + Atualizar `<button>` calling `onRefresh`; `EmptyState` when `documents.length === 0`; `<table>` with columns Documento / Motivo da rejeição / Data / Ações in `docuparse-project/frontend/src/main.jsx`
- [x] T015 [US3] Create `RejectedRow({ document, onReprocess, onDelete })` sub-component rendering filename, `document.rejection_notes ?? '—'`, formatted `document.updated_at`, and Reprocessar + Excluir action buttons in `docuparse-project/frontend/src/main.jsx`
- [x] T016 [US3] Add `handleReprocessDocument(id)` handler to `App` calling `POST /api/ocr/documents/:id/reprocess-ocr` then `refreshData()`; reuse or add `handleDeleteDocument(id)` calling `DELETE /api/ocr/documents/:id/delete` then `refreshData()` in `docuparse-project/frontend/src/main.jsx`
- [x] T017 [US3] Add Rejected view render block to `App`: `{activeView === 'rejected' ? <RejectedView documents={rejectedDocuments} onReprocess={handleReprocessDocument} onDelete={handleDeleteDocument} onRefresh={refreshData} /> : null}` in `docuparse-project/frontend/src/main.jsx`
- [x] T018 [US3] Update `document_reprocess_ocr_view`: before reprocessing, if `document.status == Document.Status.REJECTED` call `document.transition_to(Document.Status.RECEIVED)` so the document reappears in Inbox in `docuparse-project/backend-core/documents/views.py`

**Checkpoint**: Rejeitados screen lists all REJECTED documents with notes; Reprocessar returns document to Inbox; Excluir removes it permanently

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation against spec success criteria and constitution gates

- [ ] T019 Run complete `docs/specs/quickstart.md` manual test plan end-to-end (all user stories and edge cases: direct Validation access, empty Inbox, empty Rejected list)
- [ ] T020 [P] Verify constitution gates: run ESLint on `docuparse-project/frontend/src/main.jsx` (zero violations); confirm bulk-selection dead code is fully absent; run `pytest docuparse-project/backend-core/` and confirm `test_rejection_notes_in_document_list` passes

> **Implementation complete (2026-06-02)**: T001–T018 implemented. T019 requires manual testing with a running environment. T020 requires ESLint + pytest to run.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Can run in parallel with Phase 1 — does not block US1 or US2
- **Phase 3 (US1)**: Requires Phase 1 only — pure frontend, no backend dependency
- **Phase 4 (US2)**: Requires Phase 3 — ValidationView navigation relies on `selectedDocumentId` set by US1 handler
- **Phase 5 (US3)**: Requires Phase 2 (backend `rejection_notes` field) and Phase 3 (navigation pattern); T018 can run parallel with T013–T017
- **Phase 6 (Polish)**: Requires all prior phases complete

### User Story Dependencies

- **US1 (P1)**: Starts after T001 — no backend dependency
- **US2 (P2)**: Depends on US1 — `selectedDocumentId` is set by the `navigateToValidation` handler from US1
- **US3 (P3)**: Depends on Phase 2 (API field); T018 backend change independent of frontend tasks

### Within Each User Story

- **Phase 2**: T002, T003, T004 are all [P] — different files, write in parallel
- **US1 tasks**: T005 → T006 → T007 → T008 → T009 (all in main.jsx — sequential)
- **US2 tasks**: T010 → T011 → T012 (all in main.jsx — sequential)
- **US3 tasks**: T013 → T014 → T015 → T016 → T017 (main.jsx — sequential); T018 [P] with all of these (different file)

### Parallel Opportunities

- T002, T003, T004: all in different files — launch together
- T018 (views.py backend): independent from US3 frontend tasks — run alongside T013–T017
- T019 and T020: different validation activities — run in parallel

---

## Parallel Example: Backend Phase 2

```
# All three tasks target different files — launch simultaneously:
T002 → serializers.py  (rejection_notes field)
T003 → views.py        (prefetch_related queryset)
T004 → tests.py        (regression test)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 (Setup)
2. T005–T009 (US1: Inbox + navigation)
3. **STOP AND VALIDATE**: Inbox pending filter works, Upload button visible, clicking doc opens Validation
4. Deploy/demo — core navigation is functional

### Incremental Delivery

1. T001 + T005–T009 → **Inbox navigation complete (US1)**
2. T010–T012 → **Validation screen cleaned up (US2)**
3. T002–T004 + T013–T018 → **Rejected list complete (US3)**
4. T019–T020 → **All gates pass, manual test verified**

---

## Notes

- All main.jsx tasks are sequential — no intra-story parallelism for frontend
- `rejection_notes` is null-safe: `RejectedRow` must render `document.rejection_notes ?? '—'`
- Existing delete handler in `App` may already implement the `DELETE` call — check before writing a new one in T016
- Constitution Principle II requires the regression test (T004) — do not skip
- See [contracts/documents-api.md](contracts/documents-api.md) for the full `rejection_notes` API contract
- See [quickstart.md](quickstart.md) for step-by-step manual test scripts for each user story
