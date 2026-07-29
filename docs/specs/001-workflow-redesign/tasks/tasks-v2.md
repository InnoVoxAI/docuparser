# Tasks: Workflow Redesign – Ajustes Pós Implementação (v2)

**Branch**: `001-workflow-redesign` | **Date**: 2026-06-03
**Input**: [Implementation Plan v2](../implementation/implementation-workflow-redesign-plan-v2.md) · [Spec v2](../specs/workflow-redesign-v2.md)

**Prerequisites**: T001–T018 from `tasks.md` complete. No backend prerequisites. `metadata_channel` already returned by existing document detail endpoint.

**Scope**: CR-01 (metadata panel), CR-02 (real filename), CR-03 (menu reorder), CR-04 (collapsible transcriptions). CR-05 already implemented.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (not applicable here — all tasks modify `main.jsx` and must be sequential)
- **[Story]**: User story from `workflow-redesign-v2.md` (US1 = CR-01, US3 = CR-02, US4 = CR-04, US5 = CR-03)
- All tasks target `docuparse-project/frontend/src/main.jsx` — execute in order

---

## Phase 1: CR-03 — Menu Reorder (US5, P3)

**Goal**: Reorder `NAV_ITEMS` to match operational flow: Upload → Inbox → Dashboard → Rejeitados → Validação → Operações → Configurações.

**Independent Test**: Open the app and verify menu order is Upload, Inbox, Dashboard, Rejeitados, Validação, Operações, Configurações. Click each item to confirm navigation still works.

- [x] T001 [US5] Reorder the `NAV_ITEMS` array at lines 40–48 of `docuparse-project/frontend/src/main.jsx`: move `upload` to position 0, `inbox` to position 1, `dashboard` to position 2, keeping `rejected, validation, operations, settings` in positions 3–6

**Checkpoint**: Menu items display in the new order; no navigation regressions

---

## Phase 2: CR-02 — Real Filename in Viewer (US3, P2)

**Goal**: Document viewer section header shows the real filename instead of the generic "Documento" string.

**Independent Test**: Open Validation with a document selected; verify the viewer section header shows the actual filename (e.g., "N.F VANDA MOTA.pdf"). With a document lacking `original_filename`, verify the ID is shown as fallback.

- [x] T002 [US3] Replace the hardcoded `<div className="text-sm font-semibold">Documento</div>` at line 916 of `docuparse-project/frontend/src/main.jsx` with `<div className="text-sm font-semibold">{selectedDocument?.original_filename || selectedDocument?.id || 'Documento'}</div>`

**Checkpoint**: Viewer header displays real filename; ID shown when filename absent; "Documento" shown before any document is loaded

---

## Phase 3: CR-01 — DocumentMetadataPanel (US1, P1)

**Goal**: Replace the OCR technical section in ValidationView with a `DocumentMetadataPanel` component showing document and channel metadata. Remove all dead code that becomes unreachable after the replacement.

**Independent Test**: Open Validation with a document that has email metadata → verify "Metadados do Documento" section shows only non-empty fields (sender, subject, date, etc.) and no OCR engine/schema/confidence data. Open with a document without metadata → verify empty state message. Confirm Reprocessar/Excluir buttons are gone.

- [x] T003 [US1] Add the `DocumentMetadataPanel` component function to `docuparse-project/frontend/src/main.jsx` near line 1160 (after the line where `OcrMetadataBadge` currently ends): insert the full 47-line component as defined in the implementation plan Phase 1 §CR-01 §New component: `DocumentMetadataPanel`

- [x] T004 [US1] In `ValidationView` in `docuparse-project/frontend/src/main.jsx`, replace the OCR section block at lines 949–976 (the `flex flex-wrap items-start justify-between` div containing `OcrMetadataBadge`, Reprocessar/Excluir buttons, and the technical `KeyValueGrid`) with the new two-element block: `<div className="flex items-center justify-between"><StatusBadge status={selectedDocument.status} /></div>` followed by `<DocumentMetadataPanel document={selectedDocument} />`

- [x] T005 [US1] Remove the five dead symbols that have no callers after T004 from `docuparse-project/frontend/src/main.jsx`: (1) `reprocessing` state declaration, (2) `deleting` state declaration, (3) `actionMessage` state declaration, (4) `reprocessDocument` function (~lines 857–873), (5) `deleteDocument` function (~lines 875–894)

- [x] T006 [US1] Remove the `OcrMetadataBadge` function definition at lines 1160–1172 of `docuparse-project/frontend/src/main.jsx` (dead code after T004 removed its only call site at line ~955)

**Checkpoint**: Validation panel shows "Metadados do Documento" with non-empty fields only; no OCR technical data visible; no Reprocessar/Excluir buttons; empty state shown for documents without metadata; ESLint reports zero violations in affected area

---

## Phase 4: CR-04 — Collapsible Transcriptions (US4, P3)

**Goal**: Both transcription sections have independent expand/collapse toggle buttons. Content stays in DOM when collapsed (no re-fetch on expand).

**Independent Test**: Open Validation with a document; verify both sections start expanded. Click "Recolher" on "Transcrição Completa" → only that section collapses, showing "Expandir" button. Click "Expandir" → content returns without page reload. Verify "Transcrição Formatada" was unaffected. Repeat in reverse order.

- [x] T007 [US4] Replace the `ReadOnlyTranscription` function at lines 1174–1185 of `docuparse-project/frontend/src/main.jsx` with the collapsible version: adds `const [open, setOpen] = useState(true)`, a header with a toggle button (`Recolher`/`Expandir`), and applies `${open ? '' : ' hidden'}` to the `className` of the `<textarea>` (keeping the element mounted in DOM per FR-009)

- [x] T008 [US4] Replace the `ReadOnlyTranscriptionFormatted` function at lines 1188–1204 of `docuparse-project/frontend/src/main.jsx` with the collapsible version: adds `const [open, setOpen] = useState(true)`, a header with a "layout preservado" badge and a toggle button (`Recolher`/`Expandir`), and applies `${open ? '' : ' hidden'}` to the `className` of the `<pre>` element (keeping it mounted in DOM per FR-009)

**Checkpoint**: Each transcription section toggles independently; content does not reload on expand; both start expanded on first render

---

## Phase 5: Verification

**Purpose**: Confirm all four change requests pass their acceptance scenarios from `workflow-redesign-v2.md`.

- [ ] T009 Verify CR-03: Open the app and confirm menu order is Upload → Inbox → Dashboard → Rejeitados → Validação → Operações → Configurações; click all 7 items and confirm navigation works
- [ ] T010 Verify CR-02: Select a document with a filename in Validation; confirm viewer header shows filename not "Documento"; verify fallback to document ID when filename is absent
- [ ] T011 Verify CR-01: Select a document with email channel metadata; confirm "Metadados do Documento" shows only non-empty fields; no OCR technical data visible; no Reprocessar/Excluir buttons; select a document without metadata and confirm empty state message appears
- [ ] T012 Verify CR-04: Confirm both transcription sections start expanded; collapse/expand each independently; confirm collapsing one does not affect the other; confirm content does not reload on expand

---

## Dependencies & Execution Order

All tasks modify `docuparse-project/frontend/src/main.jsx` — execute strictly sequentially.

```
T001 (CR-03 NAV_ITEMS)
  → T002 (CR-02 viewer title)
    → T003 (CR-01 add DocumentMetadataPanel)
      → T004 (CR-01 replace OCR section)
        → T005 (CR-01 remove dead state/functions)
          → T006 (CR-01 remove OcrMetadataBadge)
            → T007 (CR-04 ReadOnlyTranscription)
              → T008 (CR-04 ReadOnlyTranscriptionFormatted)
                → T009–T012 (verification)
```

**Rationale for order**: Trivial/zero-risk changes first (T001, T002); new component added before its call site (T003 before T004); dead code removed after its callers are eliminated (T005, T006 after T004); transcription changes last as they are fully isolated (T007, T008).

---

## Implementation Strategy

### Safest Path (Recommended)

1. **T001** — Menu reorder: zero-risk; validates navigation fundamentals still intact before touching more complex areas
2. **T002** — Filename title: one-line change; verify viewer renders correctly
3. **T003–T006** — CR-01 metadata panel: most complex change; complete all four sub-tasks before verifying, since T005/T006 clean up dead code from T004
4. **T007–T008** — Transcription collapse: isolated, zero external dependencies
5. **T009–T012** — Acceptance verification: run against all four CRs in one pass

### Key Implementation Notes

- **T003**: The `DocumentMetadataPanel` component must be inserted before T004 wires in the call site — prevents a "component not defined" runtime error if the file is saved mid-implementation
- **T005 dead code list**: `reprocessing` and `deleting` are `useState` declarations (remove the line); `actionMessage` is also a `useState` declaration; `reprocessDocument` and `deleteDocument` are full function bodies — remove each function definition completely
- **T006**: Remove only the `OcrMetadataBadge` function definition; its import of `lucide-react` icons may be shared — do not remove imports that are still used elsewhere
- **T007/T008**: The `hidden` CSS class approach (`className={open ? '' : ' hidden'}`) keeps the DOM element mounted and satisfies FR-009 — do not use `{open && <element>}` conditional rendering
- **CR-05 excluded**: Already implemented via `filter(([, value]) => value !== '' && value !== null && value !== undefined)` guard present in `ValidationView`'s `useEffect` and `runLangExtract`

---

## Notes

- No backend tasks: `metadata_channel` is already serialized at `backend-core/documents/serializers.py:55–56`
- No new npm dependencies required
- Constitution gates already verified in implementation plan: all components ≤ 50 lines, no net dead code, no new API calls
- See [implementation plan](../implementation/implementation-workflow-redesign-plan-v2.md) for exact before/after code for each task
