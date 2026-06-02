# Implementation Plan: Workflow Redesign – Validação de Documentos

**Branch**: `001-workflow-redesign` | **Date**: 2026-06-02 | **Spec**: [workflow-redesign.md](../workflow-redesign.md)

**Input**: Feature specification from `docs/specs/workflow-redesign.md`

---

## Summary

Redesign the DocuParse frontend validation workflow to reduce operational friction.
Changes are concentrated in `main.jsx` (React SPA) with one backend serializer
update to expose rejection notes. Navigation remains state-based (`activeView`);
no routing library will be introduced. The key structural shifts are: Inbox
filtered to pending-only with an Upload shortcut above the list; Validation
reduced to single-document focus (lateral list removed) and gated behind Inbox
click; a new Rejected view for post-rejection management backed by the existing
`ValidationDecision.notes` field.

---

## Technical Context

**Language/Version**: Python 3.11 (backend-core Django), JavaScript ES2022 (React 18 + Vite)

**Primary Dependencies**: Django REST Framework, React 18, Axios 1.x, Lucide React,
Tailwind CSS (utility classes inline)

**Storage**: PostgreSQL (document state and decisions), local filesystem (document
files via `LocalStorage`)

**Testing**: pytest + pytest-django (backend); no frontend test suite in the
project — backend serializer change requires a regression test

**Target Platform**: Web browser (desktop), Docker-containerised microservices

**Project Type**: web-application (SPA) + web-service (Django backend-core)

**Performance Goals**: Status changes visible on the Rejected list within 2 s
of rejection confirmation (SC-004); Inbox → Validation navigation instant (client-side
state change only)

**Constraints**:
- No new React routing library (navigation via `activeView` state in `App`)
- No new backend microservice or endpoint — the existing documents API with
  `?status=REJECTED` filter covers rejected list; add `rejection_notes` to
  `DocumentListSerializer` only
- All changes must remain within the existing Tailwind design system

**Scale/Scope**: Single-tenant demo operation, small validation team

---

## Constitution Check

*GATE: Must pass before implementation begins. Re-check before each PR.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Code Quality | Functions ≤ 50 lines; no dead code; ESLint clean | ✅ All new components follow existing patterns; bulk-selection code removed from ValidationView (dead code eliminated) |
| II. Testing Standards | Backend serializer change needs regression test; frontend has no test suite (pre-existing gap) | ⚠️ Add `test_rejection_notes_in_document_list` in `backend-core` tests; document test gap for frontend |
| III. UX Consistency | Unified API envelope; loading/error states on all async ops; consistent terminology | ✅ Reuse existing `Alert`, `EmptyState`, `StatusBadge` components; use "Rejeitados" consistently |
| IV. Performance Requirements | No new API calls introduced; rejection notes fetched as part of existing document list query | ✅ Add `prefetch_related("validation_decisions")` to existing queryset; no extra round-trips |

**Complexity Tracking**: No violations requiring justification.

---

## Project Structure

### Documentation (this feature)

```text
docs/specs/
├── workflow-redesign.md          # Feature specification
├── research.md                   # Phase 0 output (this command)
├── data-model.md                 # Phase 1 output (this command)
├── quickstart.md                 # Phase 1 output (this command)
├── contracts/
│   └── documents-api.md          # Phase 1 output (this command)
├── implementation/
│   └── implementation-workflow-redesign.md  # This file
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
docuparse-project/
├── frontend/
│   └── src/
│       └── main.jsx              # Primary change — all UI modifications
└── backend-core/
    └── documents/
        ├── serializers.py        # Add rejection_notes to DocumentListSerializer
        └── views.py              # Add prefetch_related to documents_inbox_view
```

**Structure Decision**: Web application (Option 2). All frontend changes are in
the single `main.jsx` file following the existing monolith-component pattern.
Backend changes are minimal: one serializer field and one queryset annotation.

---

## Phase 0: Research

*All NEEDS CLARIFICATION items resolved by reading codebase directly.*

See [research.md](../research.md) for full findings.

---

## Phase 1: Design

### Backend: Rejection Notes on Document List

**File**: `docuparse-project/backend-core/documents/serializers.py`

Add `rejection_notes` as a `SerializerMethodField` on `DocumentListSerializer`:

```python
rejection_notes = serializers.SerializerMethodField()

def get_rejection_notes(self, obj: Document) -> str | None:
    # Returns the notes from the latest rejected ValidationDecision, or None.
    decisions = getattr(obj, '_prefetched_rejection_decisions', None)
    if decisions is None:
        decisions = obj.validation_decisions.filter(
            decision='rejected'
        ).order_by('-created_at')
    latest = next(iter(decisions), None)
    return latest.notes if latest else None
```

And add `"rejection_notes"` to `Meta.fields`.

**File**: `docuparse-project/backend-core/documents/views.py`

In `documents_inbox_view`, add `prefetch_related` for rejection decisions:

```python
queryset = (
    Document.objects
    .select_related("tenant", "extraction_result")
    .prefetch_related(
        models.Prefetch(
            "validation_decisions",
            queryset=ValidationDecision.objects.filter(
                decision="rejected"
            ).order_by("-created_at"),
            to_attr="_prefetched_rejection_decisions",
        )
    )
    .order_by("-received_at")
)
```

### Frontend: Component Changes in `main.jsx`

See [data-model.md](../data-model.md) and [contracts/documents-api.md](../contracts/documents-api.md) for the data shapes.

#### 1. NAV_ITEMS — Add Rejected view

```js
const NAV_ITEMS = [
    { id: 'dashboard',  label: 'Dashboard',    icon: LayoutDashboard },
    { id: 'inbox',      label: 'Inbox',         icon: Inbox },
    { id: 'upload',     label: 'Upload',        icon: Upload },
    { id: 'rejected',   label: 'Rejeitados',    icon: XCircle },
    { id: 'validation', label: 'Validacao',     icon: ClipboardCheck },
    { id: 'operations', label: 'Operacoes',     icon: AlertTriangle },
    { id: 'settings',   label: 'Configuracoes', icon: Settings },
]
```

Note: `validation` is kept in NAV_ITEMS for completeness but direct access is
guarded inside `ValidationView` (redirects to inbox if no document selected).

#### 2. App — Thread navigation through Inbox

Add `navigateToValidation` handler in `App`:

```js
const navigateToValidation = (documentId) => {
    setSelectedDocumentId(documentId)
    setActiveView('validation')
}
```

Pass it down to `InboxView`.

Change the Inbox render call:

```jsx
{activeView === 'inbox' ? (
    <InboxView
        documents={pendingDocuments}
        onNavigateToValidation={navigateToValidation}
        onNavigateToUpload={() => setActiveView('upload')}
    />
) : null}
```

Change the Rejected render call (new):

```jsx
{activeView === 'rejected' ? (
    <RejectedView
        documents={documents.filter(d => d.status === 'REJECTED')}
        onReprocess={/* reprocess handler */}
        onDelete={/* delete handler */}
        onRefresh={refreshData}
    />
) : null}
```

#### 3. InboxView — Pending only + Upload shortcut + navigation

```jsx
function InboxView({ documents, onNavigateToValidation, onNavigateToUpload }) {
    const [search, setSearch] = useState('')
    const displayed = filterDocuments(documents, search)
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <button
                    type="button"
                    onClick={onNavigateToUpload}
                    className="primary-button"
                >
                    <Upload size={16} aria-hidden="true" />
                    Enviar Documento
                </button>
            </div>
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                    <div className="text-sm font-semibold">Documentos pendentes</div>
                    <SearchInput value={search} onChange={setSearch}
                        placeholder="Buscar por nome, tipo..." />
                </div>
                <DocumentTable
                    documents={displayed}
                    onSelectDocument={onNavigateToValidation}
                />
            </section>
        </div>
    )
}
```

Key changes vs. current:
- Receives `pendingDocuments` (already filtered in `App` via `useMemo`)
- Upload button above the list (RF-11)
- `onSelectDocument` triggers `onNavigateToValidation`, which sets both `selectedDocumentId` and `activeView = 'validation'` (RF-02, RF-10)
- No `selectedDocumentId` highlight prop needed (inbox is read-only navigation)

#### 4. ValidationView — Remove lateral list; guard direct access

Remove the entire first `<section>` column (the "Fila de validacao" panel with
`DocumentTable`, bulk selection, and `validationSearch`). This removes:
- `validationSearch`, `bulkSelectedIds`, `bulkProgress` state
- `filteredValidationDocs`, `bulkDelete`, `bulkReprocess` functions
- The 340px-wide left `<section>` in the 3-column grid

The component becomes a 2-column grid (document viewer + metadata panel), or
single-column if no document selected.

Guard direct access (RF-10): if `!selectedDocumentId`, show empty state with
redirect back to inbox:

```jsx
if (!selectedDocumentId) {
    return (
        <div className="flex flex-col items-center gap-4 py-12 text-zinc-500">
            <ClipboardCheck size={40} aria-hidden="true" />
            <p className="text-sm">Selecione um documento no Inbox para iniciar a validacao.</p>
            <button
                type="button"
                onClick={onBackToInbox}
                className="primary-button"
            >
                Ir para o Inbox
            </button>
        </div>
    )
}
```

Pass `onBackToInbox={() => setActiveView('inbox')}` from `App` to `ValidationView`.

Updated grid layout (2-column):
```jsx
<div className="grid gap-4 xl:grid-cols-[minmax(360px,0.9fr)_minmax(460px,1.1fr)]">
    {/* Document viewer */}
    {/* Metadata/actions panel */}
</div>
```

Remove `documents`, `selectedDocumentId`, `onSelectDocument`, and bulk-related
props from `ValidationView`'s signature. Keep: `schemas`, `selectedDocument`,
`onDocumentUpdated`, `onDocumentDeleted`, `onValidated`, `onBackToInbox`.

#### 5. RejectedView — New component

```jsx
function RejectedView({ documents, onReprocess, onDelete, onRefresh }) {
    // documents: already filtered to REJECTED status by App
    // rejection_notes comes from document.rejection_notes (API field)
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                <div className="text-sm font-semibold">Documentos rejeitados</div>
                <button type="button" onClick={onRefresh} className="...">
                    <RefreshCw size={16} />
                    Atualizar
                </button>
            </div>
            {documents.length === 0
                ? <EmptyState icon={XCircle} text="Nenhum documento rejeitado." />
                : (
                <table className="min-w-full divide-y divide-zinc-200 text-sm">
                    <thead>
                        <tr>
                            <th>Documento</th>
                            <th>Motivo da rejeição</th>
                            <th>Data</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        {documents.map(doc => (
                            <RejectedRow
                                key={doc.id}
                                document={doc}
                                onReprocess={onReprocess}
                                onDelete={onDelete}
                            />
                        ))}
                    </tbody>
                </table>
            )}
        </section>
    )
}
```

`RejectedRow` renders per-document with Reprocessar and Excluir action buttons.
Reprocess calls `POST /api/ocr/documents/:id/reprocess-ocr` and transitions
document back to pending (then disappears from Rejected list on next `refreshData`).
Delete calls `DELETE /api/ocr/documents/:id/delete`.

---

## Validation: Metadata Display (RF-04, RF-05)

The existing `LangExtractPanel` already filters out empty values at extraction
time (`filter(([, value]) => value !== '' && value !== null && value !== undefined)`).

The `ExtractionResultSerializer.get_cleaned_fields` also strips empty values
server-side. No additional change is required for RF-05 beyond confirming this
behavior is preserved after removing the lateral panel.

---

## Quickstart Reference

See [quickstart.md](../quickstart.md) for manual test steps.

---

## API Contracts

See [contracts/documents-api.md](../contracts/documents-api.md).
