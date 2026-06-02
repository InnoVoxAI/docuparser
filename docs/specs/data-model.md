# Data Model: Workflow Redesign – Validação de Documentos

**Branch**: `001-workflow-redesign` | **Date**: 2026-06-02

---

## Entities

### Document

No schema migration required. All relevant fields already exist.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `status` | string (enum) | See status table below |
| `original_filename` | string | Displayed in Inbox and Rejected list |
| `received_at` | datetime | Used for sorting in lists |
| `updated_at` | datetime | Used for Rejected list timestamp |
| `metadata` | JSON | Contains `metadata_channel` (email/WhatsApp sender info) |
| `extraction_result` | FK → ExtractionResult | Nested in API response |

#### Status Values

| Status | Inbox (pending) | Rejected list |
|--------|----------------|---------------|
| RECEIVED | ✅ | |
| OCR_COMPLETED | ✅ | |
| EXTRACTION_COMPLETED | ✅ | |
| VALIDATION_PENDING | ✅ | |
| APPROVED | | |
| REJECTED | | ✅ |
| OCR_FAILED | | |
| LAYOUT_CLASSIFIED | | |
| ERP_* | | |

#### Status Transitions (this feature)

```
Inbox (VALIDATION_PENDING / RECEIVED / OCR_COMPLETED / EXTRACTION_COMPLETED)
    │
    │ [operator clicks Reject in ValidationView]
    ▼
REJECTED ──→ Rejected list
    │
    ├─ [operator clicks Reprocessar]
    │   └── POST /documents/:id/reprocess-ocr
    │       └── transition_to(RECEIVED)  ← new behavior (research.md §Finding: Reprocess)
    │           └── reappears in Inbox
    │
    └─ [operator clicks Excluir]
        └── DELETE /documents/:id/delete
            └── removed from system
```

---

### ValidationDecision

Stores the rejection reason. Read-only from the frontend's perspective.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `document` | FK → Document | `related_name = "validation_decisions"` |
| `decision` | enum: approved / rejected / corrected | |
| `notes` | text | Rejection reason entered by operator |
| `created_at` | datetime | |

**API surface**: `rejection_notes` is added as a computed field to
`DocumentListSerializer`, returning the `notes` of the latest
`decision='rejected'` entry for that document.

---

### ExtractionResult (unchanged)

The `get_cleaned_fields` method in the serializer already strips fields with
empty values. No changes to this model or serializer for RF-05.

---

## Frontend State

```
App state:
├── documents: Document[]          ← all documents
├── pendingDocuments: Document[]   ← useMemo: filter by pending statuses (existing)
├── rejectedDocuments: Document[]  ← useMemo: filter status === 'REJECTED' (new)
├── selectedDocumentId: string
├── selectedDocument: Document | null
├── activeView: string
└── schemas, layouts, loading, error
```

New derived state in `App`:
```js
const rejectedDocuments = useMemo(
    () => documents.filter((d) => d.status === 'REJECTED'),
    [documents]
)
```
