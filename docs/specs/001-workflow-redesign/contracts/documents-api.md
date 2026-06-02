# API Contract: Documents — Workflow Redesign

**Service**: backend-core (Django, port 8000)
**Base path**: `/api/ocr`
**Auth**: `Authorization: Bearer <VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN>`

---

## GET /documents

List documents. Used by `App.refreshData()` on mount and after actions.

### Query Parameters

| Param | Type | Description |
|-------|------|-------------|
| `status` | string (optional) | Filter by Document.Status value |
| `tenant` | string (optional) | Filter by tenant slug |

### Response — DocumentListSerializer (updated)

```json
[
  {
    "id": "uuid",
    "status": "REJECTED",
    "channel": "email",
    "original_filename": "nota_fiscal.pdf",
    "content_type": "application/pdf",
    "document_type": "nota_fiscal",
    "layout": "nf-serie-a",
    "received_at": "2026-06-01T10:00:00Z",
    "updated_at": "2026-06-02T08:30:00Z",
    "metadata_channel": { "sender": "nfe@empresa.com" },
    "extraction_result": { "schema_id": "...", "fields": {}, "confidence": 0.9 },
    "rejection_notes": "Valor total divergente do sistema ERP."
  }
]
```

**New field**: `rejection_notes` — string or null. Returns the `notes` from
the most recent `ValidationDecision` with `decision='rejected'` for this
document. Null if no rejection decision exists.

**Change required**: `DocumentListSerializer` gains `rejection_notes`
`SerializerMethodField`; `documents_inbox_view` gains `prefetch_related`
for rejection decisions.

---

## POST /documents/:id/reprocess-ocr

Re-run OCR on a document.

**Change**: When the document being reprocessed has `status='REJECTED'`,
the view now calls `document.transition_to(Document.Status.RECEIVED)` after
OCR completes. Documents in any other status keep the existing behaviour.

### Response

`DocumentDetailSerializer` — same shape as before, with updated `status` field
(`"RECEIVED"` instead of `"REJECTED"` after reprocess from Rejected list).

---

## DELETE /documents/:id/delete

Permanently delete a document. **No change** to this endpoint.

### Response

`HTTP 204 No Content`

---

## POST /documents/:id/validate

Submit a validation decision. **No change** to this endpoint for this feature.

The `notes` field in the request body is persisted as `ValidationDecision.notes`
and is subsequently returned as `rejection_notes` in the document list.

### Request Body

```json
{
  "decision": "rejected",
  "notes": "Motivo da rejeição (obrigatório para rejected)",
  "corrected_fields": {}
}
```

---

## Unchanged Endpoints (used by this feature)

| Endpoint | Used by |
|----------|---------|
| `GET /documents/:id` | ValidationView detail fetch |
| `POST /documents/:id/langextract` | ValidationView extraction |
| `GET /documents/:id/file` | Document file viewer |
