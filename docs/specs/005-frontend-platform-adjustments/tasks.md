# Tasks: Front-end e Ajustes de Plataforma

**Input**: Design documents from `docs/specs/005-frontend-platform-adjustments/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Tests**: No test tasks — not requested in spec; backend uses existing pytest suite; frontend has no CI test suite.

**Organization**: Tasks are grouped by user story (5 stories, all independent) to enable incremental implementation and validation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no conflicts)
- **[Story]**: User story label (US1–US5)
- All stories are **independent** — any can be implemented first or in parallel

---

## Phase 1: Setup & Verification

**Purpose**: Confirm file locations match the plan before making any edits. All tasks parallelizable.

- [x] T001 [P] Confirm `SIMPLE_JWT` block exists at line ~41 in `docuparse-project/backend-core/core/settings.py` (specifically `ACCESS_TOKEN_LIFETIME: timedelta(minutes=15)`)
- [x] T002 [P] Confirm `handle()` method in `docuparse-project/backend-core/users/management/commands/seed_data.py` ends with user/role creation and has no existing SchemaConfig seeding
- [x] T003 [P] Confirm `SETTINGS_TABS` array at line ~1637, "Vincular layout ao schema" section at line ~2468, and `<ReadOnlyTranscription>` call at line ~1350 in `docuparse-project/frontend/src/main.jsx`

**Checkpoint**: Actual line numbers confirmed — proceed to implementation

---

## Phase 2: Foundational

**Purpose**: No blocking cross-cutting prerequisites exist for this feature. All 5 user stories are fully independent.

**Note**: Backend changes (US1, US2) and frontend changes (US3, US4, US5) can be implemented in **any order** and in **parallel**.

*No tasks in this phase — proceed directly to user stories.*

---

## Phase 3: User Story 1 — Sessão Persistente (Priority: P1) 🎯 MVP

**Goal**: Extend JWT access token lifetime from 15 minutes to 12 hours so users stay logged in throughout their workday.

**Independent Test**: Log in → wait 15–20 minutes without interaction → perform any authenticated action → verify no redirect to login screen.

### Implementation for User Story 1

- [x] T004 [US1] Change `ACCESS_TOKEN_LIFETIME` from `timedelta(minutes=15)` to `timedelta(hours=12)` in `docuparse-project/backend-core/core/settings.py` line ~41

**Checkpoint**: Restart Django server → login → wait 16+ minutes → confirm session still active (no 401 response)

---

## Phase 4: User Story 2 — Modelos Padrão na Inicialização (Priority: P2)

**Goal**: Automatically seed `nota_fiscal_default` and `conta_agua_default` SchemaConfig records on application startup, eliminating manual onboarding steps.

**Independent Test**: Fresh install (or cleared database) → `docker compose up` → verify `SchemaConfig.objects.filter(schema_id__in=["nota_fiscal_default", "conta_agua_default"]).count() == 2`. Restart again → count still 2 (no duplicates).

### Implementation for User Story 2

- [x] T005 [US2] Add `from documents.models import SchemaConfig` import and define `DEFAULT_SCHEMAS` list (with `nota_fiscal_default` and `conta_agua_default` entries per plan.md Phase 2) at the end of `docuparse-project/backend-core/users/management/commands/seed_data.py`
- [x] T006 [US2] Add `get_or_create` loop over `DEFAULT_SCHEMAS` at the end of `handle()` in `docuparse-project/backend-core/users/management/commands/seed_data.py` (depends on T005)

**Checkpoint**: Run `python manage.py seed_data` locally → check stdout for "created schema" or "already exists" messages for both schemas → run again → confirm "already exists" for both (idempotency verified)

---

## Phase 5: User Story 3 — Abas Reorganizadas (Priority: P3)

**Goal**: Move the "OCR Referência" tab (renamed to "Documento") to the first position in Configurações → Extração, before the "Modelo" tab.

**Independent Test**: Open Configurações → Extração → verify first visible tab is "Documento" → verify second tab is "Modelo" → click "Documento" and confirm OCR reference content renders normally.

### Implementation for User Story 3

- [x] T007 [US3] In `SETTINGS_TABS` array at line ~1637 of `docuparse-project/frontend/src/main.jsx`: move `{ id: 'ocr', label: 'OCR referencia' }` to index 0 and rename its label to `'Documento'`; move `{ id: 'setup', label: 'Modelo' }` to index 1
- [x] T008 [US3] In `SETTINGS_TAB_HELP` at line ~1656 of `docuparse-project/frontend/src/main.jsx`: update the `title` field for the `'ocr'` key from `'OCR de referencia'` to `'Documento'` for consistency (depends on T007)

**Checkpoint**: Build frontend → open Configurações → Extração → "Documento" is first tab, "Modelo" is second, all other tabs unchanged

---

## Phase 6: User Story 4 — Interface de Publicação Simplificada (Priority: P4)

**Goal**: Remove the "Vincular layout ao schema" section from Configurações → Extração → Publicação, reducing visual clutter.

**Independent Test**: Navigate to Configurações → Extração → Publicação → confirm "Vincular layout ao schema" title and form fields are not rendered anywhere on the page → confirm remaining publish content ("Salvar modelo como schema") still works normally.

### Implementation for User Story 4

- [x] T009 [US4] Remove the second `<section>` block (lines ~2468–2494) containing `<div className="mb-3 text-sm font-semibold">Vincular layout ao schema</div>` and its children from the `{activeTab === 'publish' ? (...) : null}` render in `docuparse-project/frontend/src/main.jsx`

**Checkpoint**: Build frontend → navigate to Publicação tab → "Vincular layout ao schema" not visible → "Salvar modelo como schema" section still present and functional

---

## Phase 7: User Story 5 — Tela de Validação Mais Limpa (Priority: P5)

**Goal**: Remove the "Transcrição Completa" section from the document validation screen while preserving all data internally.

**Independent Test**: Open any validated document → validation screen shows "Transcrição Formatada" section as before → "Transcrição Completa" section is not rendered → `full_transcription` field still present in API response (data not lost).

### Implementation for User Story 5

- [x] T010 [US5] Remove line ~1350 (`<ReadOnlyTranscription value={selectedDocument.full_transcription} />`) from the validation screen render in `docuparse-project/frontend/src/main.jsx`; leave `<ReadOnlyTranscriptionFormatted ...>` on the next line and the `ReadOnlyTranscription` component definition intact

**Checkpoint**: Build frontend → open validation screen → "Transcrição Completa" absent → "Transcrição Formatada" visible and correct → API response still includes `full_transcription` field

---

## Phase 8: Polish & Validation

**Purpose**: Build verification, integration smoke test, and success criteria sign-off.

- [x] T011 [P] Build frontend bundle (`npm run build` in `docuparse-project/frontend`) and confirm zero compilation errors — validates all three JSX edits (US3, US4, US5) are syntactically correct
- [ ] T012 [P] Run `python manage.py seed_data` in a clean environment and verify both `nota_fiscal_default` and `conta_agua_default` appear in the admin or via `SchemaConfig.objects.all()`
- [x] T013 Walk through success criteria SC-001 to SC-007 from `docs/specs/005-frontend-platform-adjustments/spec.md` and confirm all 7 are met

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Empty — no blocking prerequisites
- **User Stories (Phases 3–7)**: All independent; can start in **any order** after Phase 1
- **Polish (Phase 8)**: Requires all user stories complete

### User Story Dependencies

- **US1 (P1)**: Independent — only touches `settings.py`
- **US2 (P2)**: Independent — only touches `seed_data.py`
- **US3 (P3)**: Independent — touches `main.jsx` lines ~1637–1656
- **US4 (P4)**: Independent — touches `main.jsx` lines ~2468–2494
- **US5 (P5)**: Independent — touches `main.jsx` line ~1350

> **Note**: US3, US4, and US5 all edit `main.jsx` but in non-overlapping regions. They can be applied in any order in a single editing session.

### Within Each User Story

- US2: T005 must complete before T006
- US3: T007 must complete before T008
- All other tasks within a story are single-step

### Parallel Opportunities

- T001, T002, T003 can all run in parallel (Phase 1)
- T004 (US1) and T005+T006 (US2) can run in parallel — different files
- T007+T008 (US3), T009 (US4), T010 (US5) are sequential in the same file but can be applied in one pass
- T011 and T012 can run in parallel (Phase 8)

---

## Parallel Example: Backend Stories (US1 + US2)

```bash
# Both can run simultaneously since they touch different files:

Task A: "Change ACCESS_TOKEN_LIFETIME to timedelta(hours=12) in settings.py (T004)"
Task B: "Add DEFAULT_SCHEMAS and get_or_create loop to seed_data.py (T005, T006)"
```

## Parallel Example: Frontend Stories (US3 + US4 + US5)

```bash
# Same file (main.jsx) — apply in one editing session, top to bottom:

Edit 1: Line ~1350 — remove ReadOnlyTranscription render (T010)
Edit 2: Lines ~1637–1656 — reorder SETTINGS_TABS and rename (T007, T008)
Edit 3: Lines ~2468–2494 — remove Vincular layout section (T009)
# Editing top-to-bottom avoids line number drift between edits
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Verification (T001–T003)
2. Complete Phase 3: US1 — change `ACCESS_TOKEN_LIFETIME` (T004) — **single line change**
3. **STOP and VALIDATE**: Login → wait 16 minutes → confirm session active
4. Deploy if ready — immediate value to all users

### Incremental Delivery

1. Verify (Phase 1) → US1 (settings.py) → Deploy: session persistence fixed
2. US2 (seed_data.py) → Deploy: models available on next container restart
3. US3 + US4 + US5 (main.jsx, one pass) → Build → Deploy: interface cleaned up
4. Polish (Phase 8) → Final sign-off

### Single-Developer Fast Path

All 5 changes can be applied in a single session (~30 minutes):

1. Edit `settings.py` (1 line)
2. Edit `seed_data.py` (~25 lines added)
3. Edit `main.jsx` (3 separate regions, one pass)
4. Build frontend
5. Validate

---

## Notes

- [P] = different files, no conflicts — safe to parallelize
- US3, US4, US5 are in the same file — apply top-to-bottom to avoid line drift
- `ReadOnlyTranscription` component definition (line ~1584) stays in `main.jsx` — only the render call at line ~1350 is removed
- `layoutForm` state and `createLayout` function stay in `main.jsx` after US4 — no unused code cleanup required for this feature
- Exact line numbers confirmed in Phase 1 before editing
- After each backend change, a container restart applies the change
- After frontend changes, `npm run build` is required before deploying to Cloudflare Pages
