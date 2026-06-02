# Research: Workflow Redesign – Validação de Documentos

**Branch**: `001-workflow-redesign` | **Date**: 2026-06-02

All unknowns resolved by reading the existing codebase directly. No external
research required.

---

## Decision: Navigation approach

**Decision**: Keep existing `activeView` state-based navigation in `App`.

**Rationale**: The project has no React Router or any other routing library.
All views are rendered via conditional JSX based on `activeView`. Introducing
a routing library would exceed the feature scope. State-based navigation is
sufficient for the Inbox → Validation flow (RF-10): the guard is implemented
by checking `selectedDocumentId` inside `ValidationView` rather than via URL
guards.

**Alternatives considered**:
- React Router (BrowserRouter): Would enable URL-based guards and bookmarkable
  views, but adds a dependency and requires a larger refactor. Rejected for
  scope reasons.

---

## Decision: Rejection notes data source

**Decision**: Use `ValidationDecision.notes` field, surfaced as `rejection_notes`
in `DocumentListSerializer` via `prefetch_related`.

**Rationale**: The `ValidationDecision` model already stores the operator's
rejection notes (the `notes` TextField). The `document_validation_view` already
persists these notes when `decision == 'rejected'`. Fetching them requires only
a prefetch on the existing document list query — no schema migration, no new
endpoint.

**Alternatives considered**:
- New `/api/ocr/documents/:id/rejection` endpoint: Over-engineered; the notes
  are already in the document's related data. Rejected.
- Store notes in `Document.metadata`: Would bypass the audit trail provided by
  `ValidationDecision`. Rejected.

---

## Decision: Rejected list data source

**Decision**: Filter existing `documents` state array in `App` for `status === 'REJECTED'`,
pass to `RejectedView`. No new API endpoint.

**Rationale**: The frontend already fetches all documents via
`GET /api/ocr/documents` and stores them in `documents` state. A computed
filter (like `pendingDocuments`) for rejected documents is free — no network call.

**Alternatives considered**:
- Dedicated `GET /api/ocr/documents?status=REJECTED` call from `RejectedView`:
  The existing endpoint already supports `?status=` filtering; this would work
  but duplicates state already in memory. Rejected for simplicity.

---

## Finding: Pending document status codes

The frontend defines pending as:
```js
['RECEIVED', 'OCR_COMPLETED', 'EXTRACTION_COMPLETED', 'VALIDATION_PENDING']
```
(line ~184 in `main.jsx`, `pendingDocuments` useMemo)

`LAYOUT_CLASSIFIED` is NOT in the pending list. `OCR_FAILED` is not pending
either. This definition is correct for Inbox — operators should only see
documents ready for human review, not those still mid-OCR pipeline.

---

## Finding: Metadata empty-field filtering (RF-05)

Already handled at two layers:
1. **Server**: `ExtractionResultSerializer.get_cleaned_fields` strips empty
   values (`""`, `None`, `[]`, `{}`) before sending to the client.
2. **Client**: `LangExtractPanel` and the `useEffect` in `ValidationView` also
   filter out empty field rows.

No additional change needed for RF-05.

---

## Finding: Reprocess on rejected document

`POST /api/ocr/documents/:id/reprocess-ocr` re-runs OCR and returns an updated
`DocumentDetailSerializer` payload. The backend does NOT automatically change
the document status to a pending state on reprocess — it returns the document
as-is with OCR results updated. The document remains `REJECTED` until manually
validated again.

**Implication for RF-08 (Reprocessar)**: After reprocess, the document should
be transitioned back to `RECEIVED` or `VALIDATION_PENDING` so it reappears in
the Inbox. Currently the reprocess endpoint does not do this transition. Two
options:

1. **Backend change**: Update `document_reprocess_ocr_view` to call
   `document.transition_to(Document.Status.RECEIVED)` after OCR completes.
2. **Frontend workaround**: After successful reprocess from `RejectedView`,
   call the validation API with `decision = 'corrected'` to set status back
   to `VALIDATION_PENDING`.

**Decision**: Option 1 is cleaner and consistent with the spec's intent
("reprocessar significa devolvê-lo ao Inbox com status pendente" — Premissas).
Include `document.transition_to(Document.Status.RECEIVED)` in the reprocess
view when called for a REJECTED document.
