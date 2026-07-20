# Contract: Zeebe Job Types ↔ Worker I/O

**Feature**: `014-bpmn-worker-flow-update`

This is the interface contract between `docuparse-pipeline` (BPMN) and
`docuparse-project/camunda-workers`. Each row is a Zeebe job type: the BPMN `zeebe:
taskDefinition type` attribute, the pyzeebe `task_type`, and the worker function's expected
inputs/outputs (`ioMapping` on the BPMN side ↔ function signature/return dict on the Python
side must match exactly, or the process will stall waiting on missing variables).

Variable names below use **process variable (camelCase)** on the BPMN side and
**Python parameter (snake_case)** on the worker side, matching the `ioMapping`
`source=`/`target=` convention already used in `flow_updated.bpmn`.

**`tenantId`/`tenant_id` is now a required input on every job type that calls
backend-core** (all except `docuparse-notify-user`, `docuparse-preprocess-image`, which
don't). `core_client()` (`workers/_http.py`) sends it as an `X-Tenant` header —
backend-core's tenant-resolution middleware (`tenants/middleware.py::_resolve_slug`)
requires it when authenticating with the internal service token, which every worker call
uses. Discovered as a live blocking bug during manual testing (job failures at
`Task_Ingestion` and beyond, `400 SuspiciousOperation: X-Tenant header is required`) —
`tenant_id` was already threaded through `docuparse-register-document` and
`docuparse-log-failure` from earlier in this feature, but no other job type had it, and
`core_client()` never attached the header regardless.

## Existing job types — extended

### `docuparse-register-document`

| | BPMN variable | Worker param/field | Type | Notes |
|---|---|---|---|---|
| in | `documentId` | `document_id` | string | unchanged |
| in | `tenantId` | `tenant_id` | string | unchanged |
| in | `fileUri` | `file_uri` | string | unchanged |
| in | `originalFilename` | `original_filename` | string | unchanged |
| in | `contentType` | `content_type` | string | unchanged |
| in | `sizeBytes` | `size_bytes` | int | unchanged |
| in | `sha256` | `sha256` | string | unchanged |
| in | `channel` | `channel` | string | unchanged |
| in | `correlationId` | `correlation_id` | string | unchanged |
| out | `docStatus` | `doc_status` | string | unchanged |
| out | `isDuplicate` | `duplicate` | bool | unchanged |
| out | **`fileValid`** | **`file_valid`** | bool | **new** — from Decision 3 |
| out | **`rejectionReason`** | **`rejection_reason`** | string | **new** — empty when `file_valid=True` |

### `docuparse-process-ocr` / `docuparse-reprocess-ocr`

| | BPMN variable | Worker param/field | Type | Notes |
|---|---|---|---|---|
| in | `documentId` | `document_id` | string | unchanged |
| in | `tenantId` | `tenant_id` | string | **new** — X-Tenant fix |
| out | `docStatus` | `doc_status` | string | unchanged |
| out | `documentType` | `document_type` | string | unchanged |
| out | `rawTextUri` | `raw_text_uri` | string | unchanged |
| out | `ocrEngine` | `ocr_engine` | string | unchanged |
| out | **`ocrReadable`** | **`ocr_readable`** | bool | **new** — from Decision 2. **T052 fix**: this output was defined in the worker return dict from the start but never mapped out of `Activity_0xc6pti`'s `ioMapping` in `flow.bpmn` — `ocrReadable` was silently `null` for every run, always taking `Gateway_0lylr3v`'s default ("Não") branch regardless of actual readability. Added the missing `<zeebe:output source="=ocr_readable" target="ocrReadable" />`. |

### `docuparse-classify-layout`

| | BPMN variable | Worker param/field | Type | Notes |
|---|---|---|---|---|
| in | `documentId` | `document_id` | string | unchanged |
| in | `tenantId` | `tenant_id` | string | **new** — X-Tenant fix (also forwarded into `resolve_schema_config_id`) |
| in | `rawTextUri` | `raw_text_uri` | string | unchanged |
| in | `documentType` | `document_type` | string | unchanged |
| out | `layout` | `layout` | string | unchanged |
| out | `layoutConfidence` | `layout_confidence` | float | unchanged |
| out | **`documentConfigured`** | **`document_configured`** | bool | **new** — from Decision 4, reuses `_resolve_schema_config_id` via shared `workers/_schema.py` |

### `docuparse-extract-fields`

Contract change: gained `tenantId` → `tenant_id` (**new** — X-Tenant fix, also forwarded
into `resolve_schema_config_id`'s fallback lookup). Otherwise kept exactly as today
(including its own internal schema-resolution fallback) as defense-in-depth for process
instances started outside the normal `Task_Layout → Gateway_01v609m` path.

**T052 fix**: the "no schema resolvable" early-return path omitted `extraction_confidence`
(and `schema_id`/`schema_version`) entirely from its return dict, leaving
`extractionConfidence` `null` — `Gateway_0kaeakc`'s `extractionConfidence > 0.95` condition
throws a `NOT_COMPARABLE` incident on `null > number`, not a graceful default-branch
fallback. Fixed by always returning `extraction_confidence: 0.0` (and empty
`schema_id`/`schema_version`) on that path, plus `or 0.0` on the success path in case
backend-core ever omits `confidence`. `Gateway_0kaeakc`'s condition is also now guarded
with `if is defined(extractionConfidence) then ... else false`, defense-in-depth. The same
incident class was hit and fixed for `Gateway_19gkipo`'s `ocrRetryCount >= 3` condition,
guarded the same way — any `>`/`>=` gateway condition needs this guard unless the variable
is *guaranteed* set on every path (equality checks like `= true` are null-safe and don't
need it).

### `docuparse-validate-document`

Gained `tenantId` → `tenant_id` (**new** — X-Tenant fix); otherwise no signature change —
this worker already accepts `decision`, `notes`, `corrected_fields`, `decided_by_id` and
returns `doc_status`. What changes is **who calls it**: it becomes wired into three
new/changed BPMN elements (`Activity_0ho24el`, and the two new "Aprovar documento" service
tasks) instead of being unreferenced by the process (Decision 6).

Call sites and their expected input values:

| BPMN element | `decision` | `notes` | `corrected_fields` |
|---|---|---|---|
| Auto-approve service task (confidence > 95%) | `"approved"` | `"auto-approved: confidence>95%"` | *(omitted)* |
| Operator-approve service task | `"approved"` | from `Task_HumanVal` form | from `Task_HumanVal` form (`correctedFields`) |
| `Activity_0ho24el` (rejected) | `"rejected"` | from `Task_HumanVal` form (required, non-empty) | *(omitted)* |

## New job types

### `docuparse-notify-user`

Used by both `Activity_0vx7jlw` (invalid file) and `Activity_12mxc87` (unreadable after
retries) — same job type, different `rejectionReason` input per path.

| | BPMN variable | Worker param | Type |
|---|---|---|---|
| in | `documentId` | `document_id` | string |
| in | `rejectionReason` | `rejection_reason` | string |
| in | `channel` | `channel` | string (routes notification to email vs WhatsApp) |
| out | `notified` | `notified` | bool |

### `docuparse-log-failure`

Used by both `Activity_10ryy35` and `Activity_07jkc9p` — writes the structured log entry
defined in `data-model.md`.

| | BPMN variable | Worker param | Type |
|---|---|---|---|
| in | `documentId` | `document_id` | string |
| in | `tenantId` | `tenant_id` | string |
| in | `rejectionReason` | `failure_reason` | string |
| in | `ocrRetryCount` | `retry_count` | int (default 0) |
| out | `loggedAt` | `logged_at` | string (ISO timestamp) |

### `docuparse-preprocess-image`

| | BPMN variable | Worker param | Type |
|---|---|---|---|
| in | `documentId` | `document_id` | string |
| in | `ocrRetryCount` | `ocr_retry_count` | int (default 0) |
| out | `ocrRetryCount` | `ocr_retry_count` | int (incremented by 1) |

### `docuparse-reset-for-reprocessing`

| | BPMN variable | Worker param | Type |
|---|---|---|---|
| in | `documentId` | `document_id` | string |
| in | `tenantId` | `tenant_id` | string (**new** — X-Tenant fix) |
| out | `docStatus` | `doc_status` | string (reset to `EXTRACTION_COMPLETED`-eligible state) |

### `docuparse-archive-document`

| | BPMN variable | Worker param | Type |
|---|---|---|---|
| in | `documentId` | `document_id` | string |
| in | `tenantId` | `tenant_id` | string (**new** — X-Tenant fix) |
| out | `docStatus` | `doc_status` | string (`"ARCHIVED"`) |

## Removed job types

### `docuparse-export-erp`

Removed from `docuparse-pipeline` (Decision 9). `erp.py` is deleted from
`camunda-workers/src/workers/`; its router registration is removed from `main.py`.
