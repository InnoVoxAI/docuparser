# Implementation Plan: Workflow Redesign – Ajustes Pós Implementação (v2)

**Branch**: `001-workflow-redesign` | **Date**: 2026-06-03 | **Spec**: [workflow-redesign-v2.md](../specs/workflow-redesign-v2.md)

**Input**: Incremental change requests (CR-01 to CR-04) on top of the completed v1 implementation. Does **not** reimplement anything already delivered in `tasks.md` (T001–T018).

**Scope**: CR-01, CR-02, CR-03, CR-04 only. CR-05 (omit empty extracted fields) is already implemented via the `filter(([, value]) => value !== '' && value !== null && value !== undefined)` guard present in `ValidationView`'s `useEffect` and `runLangExtract` — no additional work required.

---

## Summary

Four pure-frontend changes to `docuparse-project/frontend/src/main.jsx`. No backend modifications are needed: `metadata_channel` is already serialised and returned by the existing document detail endpoint (`GET /api/ocr/documents/:id`). The key structural shift is replacing the OCR technical section in `ValidationView` with a context-aware `DocumentMetadataPanel` component that renders only non-empty channel metadata fields.

| CR | Change | Risk |
|----|--------|------|
| CR-01 | Replace OCR technical panel with `DocumentMetadataPanel` | Medium — replaces an existing UI block |
| CR-02 | Real filename in document viewer section header | Low — one-line change |
| CR-03 | Reorder `NAV_ITEMS` | Trivial — array reorder |
| CR-04 | Collapsible `ReadOnlyTranscription` / `ReadOnlyTranscriptionFormatted` | Low — isolated component change |

---

## Technical Context

**Language/Version**: JavaScript ES2022 (React 18 + Vite)

**Primary Dependencies**: React 18, Lucide React, Tailwind CSS, Axios 1.x

**Storage**: N/A — read-only changes from existing `metadata_channel` JSON already persisted in PostgreSQL via `Document.metadata`

**Testing**: No frontend test suite (pre-existing gap). No backend changes → no regression tests required.

**Target Platform**: Web browser (desktop), Docker-containerised microservices

**Project Type**: SPA frontend-only changes

**Performance Goals**: No new API calls. All metadata is already fetched as part of the document detail response loaded when `selectedDocumentId` changes.

**Constraints**:
- All changes within existing Tailwind design system
- No new npm dependencies
- `metadata_channel` structure already available; no serializer changes required
- Collapse state is session-local (not persisted); React `useState` is sufficient

**Scale/Scope**: Single-tenant demo; all changes to `docuparse-project/frontend/src/main.jsx`

---

## Constitution Check

*GATE: Must pass before implementation begins.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Code Quality | Functions ≤ 50 lines; no dead code; ESLint clean | ✅ All new components stay under 50 lines; CR-01 removes `reprocessDocument`, `deleteDocument`, and `reprocessing`/`deleting`/`actionMessage` dead state from `ValidationView`; `OcrMetadataBadge` definition removed after its sole call site is gone |
| II. Testing Standards | No backend changes → no regression test required | ✅ Backend serializer untouched; constitution gate satisfied; note frontend test gap is pre-existing |
| III. UX Consistency | Unified loading/error states; existing component vocabulary | ✅ `DocumentMetadataPanel` uses existing `EmptyState` and `KeyValueGrid` patterns; `StatusBadge` is preserved in new layout |
| IV. Performance Requirements | No new API calls; no new network round-trips | ✅ `metadata_channel` already bundled in document detail response fetched by `selectedDocumentId` effect |

**Complexity note**: CR-01 removes four dead symbols from `ValidationView` (`reprocessDocument`, `deleteDocument`, `reprocessing`, `deleting`, `actionMessage`) — this is a net reduction in complexity, not an addition.

---

## Project Structure

### Documentation (this feature)

```text
docs/specs/001-workflow-redesign/
├── specs/
│   ├── workflow-redesign.md                # v1 specification (delivered)
│   └── workflow-redesign-v2.md             # v2 change requests (CR-01 to CR-04)
├── tasks/
│   └── tasks.md                            # v1 tasks (T001–T018 complete)
└── implementation/
    ├── implementation-workflow-redesign-plan.md    # v1 plan (complete)
    └── implementation-workflow-redesign-plan-v2.md # This file
```

### Source Code (single file)

```text
docuparse-project/frontend/src/
└── main.jsx    # All CR-01 to CR-04 changes go here
```

---

## Phase 0: Research (Resolved)

No unknowns. Findings from existing code:

**Decision**: Use `document.metadata_channel` field (already serialised)
- Rationale: `DocumentListSerializer.get_metadata_channel` returns `(obj.metadata or {}).get("metadata_channel")` at `backend-core/documents/serializers.py:55–56`; value is already included in the document detail response
- Field map confirmed from `EmailMetadataModal` at `main.jsx:2748–2767`:
  - `meta.sender` → Remetente
  - `meta.to` → Destinatário
  - `meta.cc` → CC
  - `meta.subject` → Assunto
  - `meta.date` → Data de envio
  - `meta.message_id` → Message-ID
  - `meta.provider` → Provedor
  - `meta.body` → Corpo do email (inferred; may be absent for non-email channels)
  - `meta.attachments` → Lista de anexos (array of filenames or objects; render as list)
- `document.original_filename` → Nome do documento
- `document.id` → Código do processo (as used in `EmailMetadataModal:2767`)

**Decision**: Collapse via CSS `hidden` class (not conditional rendering)
- Rationale: `{open ? <content /> : null}` unmounts content on collapse — violates FR-009 ("content MUST remain loaded in memory"). Using `className={open ? '' : 'hidden'}` keeps DOM element mounted with `display:none`.
- Alternatives considered: `visibility:hidden` (still takes up space), `height:0` + `overflow:hidden` (animation, more CSS surface, not needed)

**Decision**: Collapse state default = expanded
- Rationale: Acceptance scenario 1 says "When operador clica em Recolher" → implies default is expanded. State is per-section, not per-document (FR-008).

---

## Phase 1: Design

### CR-03 — `NAV_ITEMS` reorder

**Current order** (`main.jsx:40–48`): dashboard, inbox, upload, rejected, validation, operations, settings

**New order**: upload, inbox, dashboard, rejected, validation, operations, settings

Spec acceptance scenario 1 (US5):
> Upload, Inbox, Dashboard, Rejeitados, Validação, Operações, Configurações

No component changes — only the array element order.

---

### CR-02 — Document viewer section title

**Location**: `main.jsx:916` inside the left column `<section>` of `ValidationView`

**Current**:
```jsx
<div className="text-sm font-semibold">Documento</div>
```

**New**:
```jsx
<div className="text-sm font-semibold">
    {selectedDocument?.original_filename || selectedDocument?.id || 'Documento'}
</div>
```

Note: `selectedDocument` is available in this scope. The surrounding block already checks `!selectedDocument` before rendering the iframe/img — the title shows "Documento" during loading (when `selectedDocument` is null), then the real filename once loaded. No flash: the iframe already renders only when `selectedDocument` is truthy.

---

### CR-01 — Replace OCR technical section with `DocumentMetadataPanel`

#### Current block to remove from `ValidationView` (`main.jsx:949–976`)

```jsx
// Lines 949–958: filename header + OcrMetadataBadge + StatusBadge
<div className="flex flex-wrap items-start justify-between gap-3">
    <div>
        <div className="text-sm font-semibold">{selectedDocument.original_filename || selectedDocument.id}</div>
        <div className="mt-1 text-xs text-zinc-500">{selectedDocument.file_uri}</div>
    </div>
    <div className="flex flex-col items-end gap-2">
        <OcrMetadataBadge metadata={selectedDocument.ocr_metadata} processing={reprocessing} />
        <StatusBadge status={selectedDocument.status} />
    </div>
</div>
// Lines 959–968: Reprocessar OCR + Excluir buttons
<div className="flex flex-wrap items-center gap-2">
    <button ... onClick={reprocessDocument}>Reprocessar OCR</button>
    <button ... onClick={deleteDocument}>Excluir</button>
    {actionMessage ? <span ...>{actionMessage}</span> : null}
</div>
// Lines 970–976: OCR technical KeyValueGrid
<KeyValueGrid values={{ schema: ..., confidence: ..., layout: ... }} />
```

#### New block to insert

```jsx
// Status badge only — compact header
<div className="flex items-center justify-between">
    <StatusBadge status={selectedDocument.status} />
</div>
// New metadata panel (component defined below)
<DocumentMetadataPanel document={selectedDocument} />
```

#### Dead code to remove from `ValidationView`

The following symbols have no remaining callers after the block above is removed:

| Symbol | Type | Lines (approx) |
|--------|------|----------------|
| `reprocessing` | state | 766, ~857 |
| `deleting` | state | 767, ~875 |
| `actionMessage` | state | 765, ~968 |
| `reprocessDocument` | function | 857–873 |
| `deleteDocument` | function | 875–894 |

All five MUST be removed to satisfy Constitution Principle I ("No Dead Code").

#### New component: `DocumentMetadataPanel`

Place after `OcrMetadataBadge` definition (which is removed) or near `ReadOnlyTranscription`. Target: `main.jsx` near line 1160.

```jsx
function DocumentMetadataPanel({ document }) {
    const meta = document.metadata_channel || {}
    const rows = [
        { label: 'Nome do documento', value: document.original_filename },
        { label: 'Código do processo', value: document.id },
        { label: 'Remetente', value: meta.sender },
        { label: 'Destinatário', value: meta.to },
        { label: 'Assunto', value: meta.subject },
        { label: 'Data de envio', value: meta.date },
        { label: 'Message-ID', value: meta.message_id },
        { label: 'Provedor', value: meta.provider },
        { label: 'Corpo do email', value: meta.body },
    ].filter((row) => row.value != null && row.value !== '')

    const attachments = Array.isArray(meta.attachments)
        ? meta.attachments
        : meta.attachments
        ? [meta.attachments]
        : []

    const isEmpty = rows.length === 0 && attachments.length === 0

    return (
        <div className="rounded-md border border-zinc-200">
            <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">
                Metadados do Documento
            </div>
            {isEmpty ? (
                <EmptyState icon={FileText} text="Nenhum metadado disponível para este documento." />
            ) : (
                <div className="divide-y divide-zinc-100">
                    {rows.map((row) => (
                        <div key={row.label} className="grid grid-cols-[160px_1fr] gap-2 px-3 py-2">
                            <div className="text-xs font-medium text-zinc-500">{row.label}</div>
                            <div className="break-words text-sm text-zinc-800">{row.value}</div>
                        </div>
                    ))}
                    {attachments.length > 0 ? (
                        <div className="grid grid-cols-[160px_1fr] gap-2 px-3 py-2">
                            <div className="text-xs font-medium text-zinc-500">Anexos</div>
                            <div className="space-y-0.5">
                                {attachments.map((a, i) => (
                                    <div key={i} className="text-sm text-zinc-800">
                                        {typeof a === 'object' ? (a.filename || JSON.stringify(a)) : a}
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : null}
                </div>
            )}
        </div>
    )
}
```

Component is ≤ 47 lines — within the 50-line gate.

#### Remove `OcrMetadataBadge` definition

The function at `main.jsx:1160–1172` becomes dead code once its only call site (line 955) is removed. Delete it.

---

### CR-04 — Collapsible transcription sections

#### `ReadOnlyTranscription` — new implementation

```jsx
function ReadOnlyTranscription({ value }) {
    const [open, setOpen] = useState(true)
    return (
        <div className="rounded-md border border-zinc-200">
            <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                <div className="text-sm font-semibold">Transcricao completa</div>
                <button
                    type="button"
                    onClick={() => setOpen((o) => !o)}
                    className="text-xs font-medium text-zinc-500 hover:text-zinc-800"
                >
                    {open ? 'Recolher' : 'Expandir'}
                </button>
            </div>
            <textarea
                value={value || ''}
                readOnly
                className={`min-h-[160px] w-full resize-y border-0 bg-zinc-50 px-3 py-3 text-sm leading-6 text-zinc-700 outline-none${open ? '' : ' hidden'}`}
                placeholder="A transcricao aparecera aqui quando o OCR automatico concluir."
            />
        </div>
    )
}
```

#### `ReadOnlyTranscriptionFormatted` — new implementation

```jsx
function ReadOnlyTranscriptionFormatted({ value }) {
    const [open, setOpen] = useState(true)
    return (
        <div className="rounded-md border border-zinc-200">
            <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
                <span className="text-sm font-semibold">Transcricao formatada</span>
                <div className="flex items-center gap-2">
                    <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500">layout preservado</span>
                    <button
                        type="button"
                        onClick={() => setOpen((o) => !o)}
                        className="text-xs font-medium text-zinc-500 hover:text-zinc-800"
                    >
                        {open ? 'Recolher' : 'Expandir'}
                    </button>
                </div>
            </div>
            <pre className={`min-h-[160px] max-h-[420px] w-full overflow-auto whitespace-pre bg-zinc-50 px-3 py-3 text-xs leading-5 text-zinc-700${open ? '' : ' hidden'}`}>
                {value || ''}
            </pre>
            {!value ? (
                <div className="px-3 pb-3 text-xs text-zinc-400">
                    Disponivel apenas para PDFs digitais processados pelo engine Docling.
                </div>
            ) : null}
        </div>
    )
}
```

Both components: `useState(true)` → start expanded; `hidden` CSS class on collapse keeps DOM element mounted (FR-009 compliant); toggle state is independent between sections (FR-008 compliant).

---

## Implementation Order

All tasks target `main.jsx` → fully sequential.

```
T001: CR-03 — Reorder NAV_ITEMS (5 min)
T002: CR-02 — Real filename in viewer title (5 min)
T003: CR-01 — Add DocumentMetadataPanel component (15 min)
T004: CR-01 — Replace OCR section in ValidationView; remove dead state/functions (20 min)
T005: CR-01 — Remove OcrMetadataBadge definition (2 min)
T006: CR-04 — Make ReadOnlyTranscription collapsible (10 min)
T007: CR-04 — Make ReadOnlyTranscriptionFormatted collapsible (10 min)
T008: Manual verification against spec acceptance scenarios (30 min)
```

**Rationale for order**: Trivial / zero-risk first (T001, T002); new component added before it's wired (T003 before T004); dead code cleanup after its callers are gone (T005 after T004); transcription changes last as they're purely isolated (T006, T007).

---

## Constitution Check — Post Design

| Principle | Gate | Status |
|-----------|------|--------|
| I. Code Quality | `DocumentMetadataPanel` = 47 lines ✓; `ReadOnlyTranscription` = 20 lines ✓; `ReadOnlyTranscriptionFormatted` = 23 lines ✓; removes 5 dead symbols from `ValidationView` ✓ | ✅ |
| II. Testing Standards | No backend change; no regression test required | ✅ |
| III. UX Consistency | `EmptyState`, `StatusBadge` reused; loading/error states unaffected; field filtering is display-only | ✅ |
| IV. Performance | No new API calls; metadata_channel already in document detail payload | ✅ |

---

## Acceptance Verification Checklist

Verify each spec acceptance scenario manually after implementation:

**CR-01 (Metadados do Documento)**:
- [ ] Given a document with channel metadata → "Metadados do Documento" section shows only non-empty fields
- [ ] Given a document without channel metadata → section shows empty state message
- [ ] No OCR engine name, hint, schema ID, confidence, or layout is visible in that section

**CR-02 (Real filename in viewer)**:
- [ ] Given a document with `original_filename` → viewer section header shows the filename
- [ ] Given a document without `original_filename` → viewer section header shows document ID as fallback

**CR-03 (Menu reorder)**:
- [ ] Menu order is: Upload, Inbox, Dashboard, Rejeitados, Validação, Operações, Configurações
- [ ] Each menu item still navigates correctly

**CR-04 (Collapsible transcriptions)**:
- [ ] Both transcription sections start expanded
- [ ] Clicking "Recolher" on one section collapses only that section
- [ ] Clicking "Expandir" restores the content without page reload
- [ ] Collapsing one section does not affect the other
