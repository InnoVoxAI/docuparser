# Data Model: DocuParse Pipeline — Updated BPMN Flow & Worker Reconciliation

**Feature**: `014-bpmn-worker-flow-update` | **Date**: 2026-07-19

This feature is primarily an orchestration/integration change (Zeebe process ↔ existing
backend-core domain model), not a new domain. The entities below are either extensions of
existing backend-core models (`docuparse-project/backend-core/documents/models.py`) or
process-scoped values that live only as Zeebe process variables and are never persisted.

## Persisted entities (backend-core, Django/PostgreSQL)

### Document (extended)

Existing model (`documents/models.py:31-45`). No fields are removed or renamed.

| Field | Change | Notes |
|---|---|---|
| `status` | **extend enum** | Add `Status.ARCHIVED` (Decision 7). Existing values (`RECEIVED`, `OCR_COMPLETED`, `OCR_FAILED`, `LAYOUT_CLASSIFIED`, `EXTRACTION_COMPLETED`, `VALIDATION_PENDING`, `APPROVED`, `REJECTED`) are unchanged. `ERP_INTEGRATION_REQUESTED`/`ERP_SENT`/`ERP_FAILED` become unused by this pipeline (Decision 9) but are **not removed** — other tenants/flows or historical records may still reference them. |
| `file_valid` | **new field** | Boolean, nullable (unset until the validity check runs). Set by the new ingestion validity check (Decision 3). |
| `rejection_reason` | **new field** | Short text, nullable. Human-readable reason set alongside `file_valid=False`, or on terminal OCR-unreadable failure. |
| `ocr_readable` | **new field** | Boolean, nullable. Set by the OCR pipeline once text is available (Decision 2). |

**State transitions** (informal — `transition_to` performs no validation today, so this
table documents the *intended* flow, not an enforced state machine):

```
RECEIVED → (validity check) → REJECTED [file_valid=False] | RECEIVED [file_valid=True]
RECEIVED → OCR_COMPLETED [ocr_readable=True] | OCR_FAILED [ocr_readable=False, after 3 retries]
OCR_COMPLETED → LAYOUT_CLASSIFIED
LAYOUT_CLASSIFIED → EXTRACTION_COMPLETED
EXTRACTION_COMPLETED → APPROVED [confidence > 0.95, auto] | VALIDATION_PENDING [confidence <= 0.95]
VALIDATION_PENDING → APPROVED [operator approves] | REJECTED [operator rejects]
REJECTED → EXTRACTION_COMPLETED [operator chooses reprocess] | ARCHIVED [operator chooses delete]
```

### ValidationDecision (existing, reused — no changes)

`documents/models.py` (backing `document_validation_view`). Already supports everything
Decision 6 needs: `decision` (`approved`/`rejected`/`corrected`), `notes`,
`corrected_fields`, `decided_by_id`. No schema change required — this feature only adds
*callers* of the existing `/validate` endpoint that weren't there before.

### LayoutConfig / SchemaConfig (existing, reused — no changes)

`documents/models.py:256-286`. `LayoutConfig(layout, document_type, schema_config,
is_active)` is the existing representation of "an extraction template is configured for
this document type." Decision 4 reuses this exactly as-is; "unconfigured" continues to mean
"no active `LayoutConfig` row matches," with no new sentinel value introduced.

## Process-scoped values (Zeebe process variables — not persisted to any database)

These exist only for the lifetime of one process instance. They are not backend-core model
fields and require no migration.

| Variable | Type | Set by | Read by |
|---|---|---|---|
| `ocrRetryCount` | integer (default `0`) | `docuparse-preprocess-image` output (increments each retry) | `Gateway_19gkipo` condition |
| `fileValid` | boolean | `docuparse-register-document` output | `Gateway_1hajqec` condition |
| `rejectionReason` | string | `docuparse-register-document` / `docuparse-preprocess-image` (terminal-failure path) output | `docuparse-notify-user`, `docuparse-log-failure` inputs |
| `ocrReadable` | boolean | `docuparse-process-ocr` output | `Gateway_0lylr3v` condition |
| `documentConfigured` | boolean | `docuparse-classify-layout` output | `Gateway_01v609m` condition |
| `approved` | boolean | `Task_HumanVal` Tasklist form output | `Gateway_0vi5mc1` condition |
| `correctedFields` | JSON object | `Task_HumanVal` Tasklist form output | `docuparse-validate-document` input on the rejected/approved paths |
| `reprocessChoice` | string (`"reprocess"` \| `"delete"`) | Tasklist form or upstream decision variable | `Gateway_1qmnvbm` condition |

## Structured log schema (basic logging only — not a database entity, no observability platform integration)

No observability platform (Grafana or otherwise) is actually wired up yet — the flow
diagram's annotation naming one is aspirational. `docuparse-log-failure` therefore does
**basic structured logging only**: it writes a structured event via `structlog` (already
the project's logging convention in every worker) to the process's normal log output. That
output can be picked up by whatever log aggregation/observability tooling is stood up later
— this feature does not add any HTTP call, SDK, or integration to a specific platform:

| Field | Description |
|---|---|
| `document_id` | Identifies the failed document |
| `tenant_id` | Tenant scope |
| `failure_reason` | e.g. `"invalid_file"`, `"unreadable_after_retries"` |
| `failure_step` | BPMN element that raised the failure (`Task_Ingestion`, `Task_OCR`) |
| `retry_count` | Value of `ocrRetryCount` at time of failure (0 for validity failures) |
