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
| out | `docStatus` | `doc_status` | string | unchanged |
| out | `documentType` | `document_type` | string | unchanged |
| out | `rawTextUri` | `raw_text_uri` | string | unchanged |
| out | `ocrEngine` | `ocr_engine` | string | unchanged |
| out | **`ocrReadable`** | **`ocr_readable`** | bool | **new** — from Decision 2 |

### `docuparse-classify-layout`

| | BPMN variable | Worker param/field | Type | Notes |
|---|---|---|---|---|
| in | `documentId` | `document_id` | string | unchanged |
| in | `rawTextUri` | `raw_text_uri` | string | unchanged |
| in | `documentType` | `document_type` | string | unchanged |
| out | `layout` | `layout` | string | unchanged |
| out | `layoutConfidence` | `layout_confidence` | float | unchanged |
| out | **`documentConfigured`** | **`document_configured`** | bool | **new** — from Decision 4, reuses `_resolve_schema_config_id` via shared `workers/_schema.py` |

### `docuparse-extract-fields`

No contract change. Kept exactly as today (including its own internal schema-resolution
fallback) as defense-in-depth for process instances started outside the normal
`Task_Layout → Gateway_01v609m` path.

### `docuparse-validate-document`

No signature change — this worker already accepts `decision`, `notes`,
`corrected_fields`, `decided_by_id` and returns `doc_status`. What changes is **who calls
it**: it becomes wired into three new/changed BPMN elements (`Activity_0ho24el`, and the two
new "Aprovar documento" service tasks) instead of being unreferenced by the process (Decision
6).

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
| out | `docStatus` | `doc_status` | string (reset to `EXTRACTION_COMPLETED`-eligible state) |

### `docuparse-archive-document`

| | BPMN variable | Worker param | Type |
|---|---|---|---|
| in | `documentId` | `document_id` | string |
| out | `docStatus` | `doc_status` | string (`"ARCHIVED"`) |

## Removed job types

### `docuparse-export-erp`

Removed from `docuparse-pipeline` (Decision 9). `erp.py` is deleted from
`camunda-workers/src/workers/`; its router registration is removed from `main.py`.
