# Research: DocuParse Pipeline — Updated BPMN Flow & Worker Reconciliation

**Feature**: `014-bpmn-worker-flow-update` | **Date**: 2026-07-19

## Method

`docuparse-project/bpmn/flow.bpmn` (deployed) was diffed against
`docuparse-project/bpmn/flow_updated.bpmn` (target), the existing worker modules under
`docuparse-project/camunda-workers/src/workers/` were read in full, and the backend-core
Django service they call (`docuparse-project/backend-core/documents/`) was searched for the
data/behavior each new gateway needs. Findings below are organized as Decisions (with
rationale and alternatives), followed by a full task-by-task gap analysis of the updated
BPMN.

---

## Decision 1: Reprocess/retry counter is a Zeebe process variable, not a DB field

**Decision**: The "image already processed 3x?" gate (`Gateway_19gkipo`) is driven by a
process variable (`ocrRetryCount`, default `0`), incremented by the new image
pre-processing worker and read by the gateway's condition expression.

**Rationale**: The counter is meaningless outside the lifetime of one process instance —
it doesn't need to be queried, reported on, or survive the process ending. Zeebe already
carries process variables through the instance at no extra cost. Backend research
(`documents/models.py`) confirms `Document` has no such field today, and adding one would
require a migration for a value nothing outside this BPMN gateway ever reads.

**Alternatives considered**: Persist `ocr_retry_count` on `Document` — rejected as
unnecessary schema/migration scope creep for a transient counter; would also require the
backend to be the source of truth for a value Zeebe already tracks natively.

---

## Decision 2: OCR "readability" is a new signal computed in backend-core, forwarded by the OCR worker

**Decision**: `Gateway_0lylr3v` ("Documento legível?") needs a boolean the OCR worker
doesn't currently produce. Backend research confirms **no legibility/OCR-confidence concept
exists anywhere today** — `process_document_ocr` (`documents/services/ocr_processor.py`)
unconditionally sets `OCR_COMPLETED` regardless of text quality. `LayoutConfig
.confidence_threshold` exists but is dead code (never read). The `docuparse-process-ocr` /
`docuparse-reprocess-ocr` workers must be extended to return a new `ocr_readable: bool`
field, sourced from a new backend-core computation (e.g., non-empty extracted text above a
minimum character/word threshold, or an OCR-engine-reported confidence score if available).

**Rationale**: The gateway can't evaluate what the API never returns. This is the one place
this feature's worker-side scope has a hard backend-core dependency — flagged explicitly so
it isn't missed during implementation/task breakdown.

**Alternatives considered**: Compute readability heuristically inside the worker itself
(e.g., inspect `raw_text_uri` contents from worker-side) — rejected because it duplicates
domain logic that belongs with the OCR pipeline in backend-core and would require the
worker to fetch and parse potentially large text blobs directly from storage.

---

## Decision 3: File-validity check is a new signal, computed at ingestion, forwarded by the register-document worker

**Decision**: `Gateway_1hajqec` ("Arquivo válido para processamento?") needs `fileValid`
and a rejection reason. Backend research confirms `consume_document_received`
(`documents/services/event_consumers.py`) trusts the incoming payload verbatim today — no
format/corruption/password-protection check exists. `docuparse-register-document` must be
extended to surface `file_valid: bool` and `rejection_reason: str` from a new backend-core
validation step performed during/after registration.

**Rationale**: Same reasoning as Decision 2 — the check belongs where the file is actually
opened (backend-core/backend-ocr), not duplicated into worker code operating on URIs.

**Alternatives considered**: Validate in the worker using only metadata already present
(`content_type`, `size_bytes`) as a lightweight allow-list check without opening the file —
viable as an interim/partial implementation (catches unsupported MIME types and zero-byte
files) but cannot detect corruption or password-protection, which requires opening the file.
Documented as an acceptable phased approach: worker-side metadata check now, backend-core
deep validation as a fast-follow.

---

## Decision 4: "Documento configurado docuparser?" reuses the existing schema-resolution logic, exposed one step earlier

**Decision**: `Gateway_01v609m` needs a `documentConfigured: bool`. This resolution already
exists — `extraction.py::_resolve_schema_config_id` calls `GET /api/ocr/layout-configs` and
matches on `(layout, document_type, is_active)`, which is exactly backend-core's
`LayoutConfig` model (`documents/models.py`). The new flow needs this decision made
**right after classification**, not buried inside the extraction worker. Extract the lookup
into a shared helper (`workers/_schema.py`) used by both `docuparse-classify-layout` (new
output: `documentConfigured`) and `docuparse-extract-fields` (kept as a defense-in-depth
fallback for direct/manual process starts).

**Rationale**: Avoids duplicating the lookup logic (constitution: no dead code / DRY) while
matching the new flow's earlier decision point. "Configured" == an active `LayoutConfig`
row exists for the classified `(layout, document_type)`; "unconfigured" == no matching row
(there is no separate "unconfigured" flag in backend-core — confirmed).

**Alternatives considered**: Duplicate the lookup inline in `layout.py` — rejected, violates
DRY for no benefit since both workers hit the identical backend-core endpoint.

---

## Decision 5: Template resolution (`Activity_1hafvqe`) and document deletion (`Activity_142wpxf`) are native Camunda user tasks — no Python job worker needed for the tasks themselves

**Decision**: Both elements are modeled as `<bpmn:userTask>` with a bare `<zeebe:userTask/>`
marker and no `<zeebe:taskDefinition>` — in Zeebe 8.5+ (this project runs Camunda 8.6, per
`docker-compose.yml`) that makes them **Camunda-managed user tasks**, completed via
Tasklist/its REST API, not pyzeebe job workers. No worker code is needed for the task itself;
whatever fields the Tasklist form captures become process variables automatically.

**Rationale**: Matches `validation.py`'s own existing docstring convention ("For
human-driven validation use a `<userTask>` in the BPMN instead — Tasklist handles it"),
which the team already established for `Task_HumanVal`.

**Note — data quality issue in the source diagram**: `Activity_1hafvqe`'s `ioMapping`
currently lists outputs (`schema_id`, `extraction_confidence`,
`extraction_requires_human_validation`, `extraction_skipped`) that are an exact copy of
`Task_Extraction`'s outputs — almost certainly copy-pasted in error, since an operator
creating/selecting a template wouldn't be producing an extraction confidence score. This
should be corrected to just `schemaId` (the template the operator picked or created) when
the BPMN is next edited. Flagged for the diagram owner; not a worker-code change.

**Alternatives considered**: Convert both to job-worker-backed tasks — rejected; there's no
automated system today that can create/select a template or authoritatively delete a
document without a person, and converting would contradict the spec decisions already made
with the user (operator-driven template resolution; operator-driven delete choice).

---

## Decision 6: Two BPMN wiring gaps must close for validation decisions to actually persist

**Decision**: Reconciling workers with this flow surfaces two places where the diagram
routes to an end event or to `Activity_0ho24el` without ever calling
`docuparse-validate-document` — meaning `ValidationDecision` records and `Document.status`
transitions (`APPROVED`/`REJECTED`) would never actually happen despite the diagram visually
implying it:

1. **Rejected branch**: `Activity_0ho24el` ("Status do documento = Rejeitado") is already a
   bare `serviceTask` with no `taskDefinition` — the natural, minimal fix is to wire its
   `zeebe:taskDefinition` to the existing `docuparse-validate-document` job type
   (`decision="rejected"`, forwarding `notes`/`correctedFields` captured on the
   `Task_HumanVal` Tasklist form).
2. **Approved branches** (`Flow_1tw1rhb` from the confidence gate, and `Flow_1n0hpsg` from
   the operator-approval gate) both currently flow straight to `Event_15yo9c3` with no
   service task in between — nothing ever calls `/validate` with `decision="approved"`. A
   new `serviceTask` (job type: `docuparse-validate-document`, `decision="approved"`) needs
   to be inserted on both paths before the end event.

**Rationale**: `document_validation_view` (`documents/views.py`) is the only mechanism in
backend-core that writes a `ValidationDecision` and transitions `Document.status` to
`APPROVED`/`REJECTED`. Without these calls, User Story 4 and User Story 5's acceptance
criteria ("document is marked processed", "document status is set to rejected") are not
actually satisfiable by the diagram as drawn.

**Rationale for reusing `docuparse-validate-document` rather than adding new job types**:
The worker already exists, is already documented for exactly this purpose ("This worker
handles automated or post-human-task programmatic decisions"), and its backend contract
(`decision`, `notes`, `corrected_fields`, `decided_by_id`) already covers both the
auto-approve path (`decision="approved"`, `notes="auto-approved: confidence>95%"`) and the
operator-decision paths.

**Alternatives considered**: Leave the diagram as-is and treat "marked processed" as purely
a Zeebe-level status with no backend persistence — rejected, contradicts SC-003/SC-004 in
the spec (submitter must be informed the document was *sent*, which backend-core's
downstream consumers key off `Document.status`).

---

## Decision 7: Document deletion uses a new soft-delete/archive endpoint and job type — the existing hard-delete worker is not reused

**Decision**: The user selected soft-delete/archive semantics (record and file retained).
Backend research confirms the existing `DELETE /api/ocr/documents/{id}/delete` +
`docuparse-delete-document` worker perform a **hard** delete (`document.delete()`, cascading
storage cleanup via `documents/signals.py`) — the opposite of what's needed here. This
requires:
- A new `Document.Status.ARCHIVED` choice (backend-core, additive, non-breaking).
- A new backend-core endpoint (e.g. `POST /api/ocr/documents/{id}/archive`) that sets status
  to `ARCHIVED` without deleting the row or invoking the storage-cleanup signal.
- A new worker job type `docuparse-archive-document`, wired to a **new** `serviceTask`
  inserted after `Activity_142wpxf`'s Tasklist confirmation (the userTask itself has no
  job-worker hook to attach to — see Decision 5), before `Event_07z8dpg`.

**Rationale**: Reusing `docuparse-delete-document` would silently hard-delete despite the
product decision being soft-delete; keeping both workers is clearer than overloading one
task type with different semantics based on a flag.

**Alternatives considered**: Add an `archived: bool` flag to the existing hard-delete
endpoint/worker instead of a new status+endpoint — rejected; `Document.status` is already
the system's single source of truth for lifecycle state (confirmed via `transition_to`
helper), so a parallel boolean flag would fork that source of truth for no benefit.

---

## Decision 8: Exclusive gateway condition expressions are in scope as a companion BPMN change

**Decision**: None of the new/changed exclusive gateways in `flow_updated.bpmn`
(`Gateway_1hajqec`, `Gateway_0lylr3v`, `Gateway_19gkipo`, `Gateway_01v609m`,
`Gateway_0kaeakc`, `Gateway_0vi5mc1`, `Gateway_1qmnvbm`) currently carry a
`<bpmn:conditionExpression>` on their outgoing sequence flows — the "Sim"/"Não" labels are
visual only. Reconciling the workers is necessary but not sufficient: the diagram won't
route deterministically until each sequence flow gets a FEEL condition referencing the exact
variable names this plan defines (`contracts/gateway-conditions.md`), and each gateway gets
a default flow for safety.

**Rationale**: Worker output variable names are meaningless to the process engine unless
gateway conditions reference them. This is a small, additive, low-risk BPMN edit (no
existing element renamed/removed) that has to ship alongside the worker code for the flow to
function at all.

**Alternatives considered**: Leave gateway wiring to a separate/future change — rejected;
shipping worker changes without functioning gateway conditions would leave the pipeline
unable to route through Zeebe at all, making the workers unreachable for testing.

---

## Decision 9: ERP export worker is decommissioned, not deleted

**Decision**: Per the spec (FR-020) and user confirmation, `docuparse-export-erp` is
removed from `docuparse-pipeline`. Backend research confirms this is safe to do cleanly:
`document_validation_view` never references ERP concerns (`IntegrationSettings` and
`erp_publisher.py`/`approved_exporter.py` are independent, tenant-scoped concerns not
touched by `/validate`). `erp.py` and its `export_erp` router registration in `main.py` are
removed from the active worker set; the module is deleted from `src/workers/` rather than
merely unregistered, since the constitution's "No Dead Code" principle prohibits unused
code sitting in the tree.

**Rationale**: Nothing else in backend-core depends on the worker calling `/validate` a
second time for ERP purposes; the underlying `/validate` call this worker used to make is
now handled by Decision 6's new service tasks instead.

**Alternatives considered**: Keep `erp.py` unregistered "for reference" — rejected per
constitution's no-dead-code rule; git history preserves it if ever needed again.

---

## Task-by-task gap analysis (flow_updated.bpmn → worker reconciliation)

| BPMN Element | Type | Current `taskDefinition` | Reconciliation needed |
|---|---|---|---|
| `Task_Ingestion` (Receber documento) | serviceTask | `docuparse-register-document` (exists) | Extend output: add `file_valid`, `rejection_reason` (Decision 3) |
| `Gateway_1hajqec` (Arquivo válido?) | gateway | — | Add condition expressions on `Flow_171awgt`/`Flow_1r61p02` referencing `fileValid` (Decision 8) |
| `Activity_0vx7jlw` (Notificar usuário — invalid) | serviceTask | none | New job type `docuparse-notify-user` |
| `Activity_10ryy35` (Salvar erro — invalid) | serviceTask | none | New job type `docuparse-log-failure` |
| `Activity_0xc6pti` (Ler documento OCR) | serviceTask | `docuparse-process-ocr` (exists) | Extend output: add `ocr_readable` (Decision 2) |
| `Gateway_0lylr3v` (Documento legível?) | gateway | — | Add conditions referencing `ocrReadable` (Decision 8) |
| `Gateway_19gkipo` (processada 3x?) | gateway | — | Add conditions referencing `ocrRetryCount >= 3` (Decisions 1, 8) |
| `Activity_0dgit79` (Pré processar/tratar imagem) | serviceTask | none | New job type `docuparse-preprocess-image`; increments/returns `ocrRetryCount` |
| `Activity_12mxc87` (Notificar usuário — unreadable) | serviceTask | none | Reuse `docuparse-notify-user` |
| `Activity_07jkc9p` (Salvar erro — unreadable) | serviceTask | none | Reuse `docuparse-log-failure` |
| `Task_Layout` (Identificar tipo) | serviceTask | `docuparse-classify-layout` (exists) | Extend output: add `documentConfigured` (Decision 4) |
| `Gateway_01v609m` (Documento configurado?) | gateway | — | Add conditions referencing `documentConfigured` (Decision 8) |
| `Activity_1hafvqe` (Criar/usar modelo) | userTask | none (native Tasklist) | No job worker; fix copy-pasted `ioMapping` outputs when BPMN is next edited (Decision 5) |
| `Gateway_0xe8zt4` (merge) | gateway | — | No condition needed (unconditional merge) |
| `Task_Extraction` (Extrair dados) | serviceTask | `docuparse-extract-fields` (exists) | No change; keep fallback schema resolution as defense-in-depth |
| `Gateway_0kaeakc` (Confiança > 95%?) | gateway | — | Add conditions referencing `extractionConfidence` (Decision 8) |
| *(new)* Aprovar documento — auto path | serviceTask | — | **New element**: `docuparse-validate-document`, `decision="approved"` before `Event_15yo9c3` (Decision 6) |
| `Task_HumanVal` (Validar dados) | userTask | none (native Tasklist) | No job worker; form must capture `approved`, `correctedFields`, `notes` |
| `Gateway_0vi5mc1` (aprovados?) | gateway | — | Add conditions referencing `approved` (Decision 8) |
| *(new)* Aprovar documento — operator path | serviceTask | — | **New element** or reuse the auto-path task via a converging gateway: `docuparse-validate-document`, `decision="approved"` before `Event_15yo9c3` (Decision 6) |
| `Activity_0ho24el` (Status = Rejeitado) | serviceTask | none | Wire to `docuparse-validate-document`, `decision="rejected"` (Decision 6) |
| `Gateway_1qmnvbm` (Apagar ou reprocessar?) | gateway | — | Add conditions referencing operator's choice variable, e.g. `reprocessChoice` (Decision 8) |
| `Activity_00oy1fz` (Reprocessar documento) | serviceTask | none | New job type `docuparse-reset-for-reprocessing` — clears prior extraction/validation result, resets status, before re-entering `Task_Extraction` via `Gateway_0xe8zt4` |
| `Activity_142wpxf` (Apagar documento) | userTask | none (native Tasklist) | No job worker for the task itself |
| *(new)* Arquivar documento | serviceTask | — | **New element** after `Activity_142wpxf`: `docuparse-archive-document` (Decision 7), before `Event_07z8dpg` |
| *(removed)* `Task_ERP` / ERP export | — | `docuparse-export-erp` | Removed from this process entirely (Decision 9) |

## Resolved unknowns

All "NEEDS CLARIFICATION" items from the spec were resolved with the user before planning
began (see `spec.md` — operator-driven template resolution, soft-delete/archive semantics,
intentional ERP removal). No open unknowns remain for Phase 1.
