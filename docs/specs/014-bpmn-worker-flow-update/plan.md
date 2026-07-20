# Implementation Plan: DocuParse Pipeline — Updated BPMN Flow & Worker Reconciliation

**Branch**: `014-bpmn-worker-flow-update` | **Date**: 2026-07-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `docs/specs/014-bpmn-worker-flow-update/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

`docuparse-project/bpmn/flow_updated.bpmn` replaces the deployed `flow.bpmn` with a much
richer `docuparse-pipeline`: a file-validity gate, an OCR-readability gate with a 3x
automatic image-preprocessing retry loop, an operator-driven template-resolution branch, a
95%-confidence auto-approval split, an operator reject/reprocess/archive loop, and
observability logging on every terminal failure — while dropping the old automated ERP
export step entirely. Reconciling `docuparse-project/camunda-workers` with this flow means:
extending three existing job workers with new output fields the new gateways need
(`file_valid`, `ocr_readable`, `document_configured`), adding five new job workers for
steps that currently have no `zeebe:taskDefinition` at all, wiring the previously-orphaned
`docuparse-validate-document` worker into the approve/reject paths so decisions actually
persist, replacing hard-delete with a new soft-delete/archive worker+endpoint, and removing
the ERP worker. Because none of the new/changed gateways currently carry executable FEEL
conditions, this plan also treats the small, additive BPMN condition-expression wiring
(`contracts/gateway-conditions.md`) as an in-scope companion change — worker code alone
cannot make the process route without it.

## Technical Context

**Language/Version**: Python 3.12 (per `camunda-workers/Dockerfile`, `python:3.12-slim`); requires 3.11+ per constitution Technology Standards.

**Primary Dependencies**: `pyzeebe==4.4.0` (Zeebe job-worker framework), `httpx==0.27.2` (async HTTP client to backend-core/layout-service/langextract-service), `structlog==24.4.0` (structured logging — reused for the new `docuparse-log-failure` job), `pydantic`/`pydantic-settings==2.3.4` (config). No new dependencies required for the worker-side changes; the soft-delete endpoint and readability/validity signals require corresponding (out-of-folder) changes in `backend-core` (Django/DRF, already a dependency of this repo).

**Storage**: N/A directly (workers are stateless request/response job handlers); indirectly PostgreSQL via backend-core's `Document`, `ValidationDecision`, `LayoutConfig`/`SchemaConfig` models (`docuparse-project/backend-core/documents/models.py`), which this plan extends with one new status value and two new nullable fields (see `data-model.md`).

**Testing**: pytest (constitution-mandated; **gap** — no `tests/` directory currently exists under `camunda-workers/`, see Constitution Check below). `respx` or `pytest-httpx` recommended for mocking the `httpx.AsyncClient` calls to backend-core without real network calls (constitution: "Unit Tests MUST NOT make network calls").

**Target Platform**: Dockerized Linux service (`python:3.12-slim`), orchestrated via `docuparse-project/docker-compose.yml`'s `camunda` profile alongside Zeebe 8.6, Operate 8.6, Tasklist 8.6.

**Project Type**: Single backend service (Zeebe job-worker pool) integrating with existing microservices (backend-core, backend-ocr, layout-service, langextract-service) — matches "Option 1: Single project" below, with companion touch points in `backend-core` and the `bpmn/` directory rather than a second worker project.

**Performance Goals**: No new throughput target introduced; inherits existing worker tuning (`worker_max_jobs=5`, `worker_poll_interval_ms=100`, `config.py`). New job types use short, backend-delegated calls (validity/readability checks piggyback on existing `/process-ocr`/registration responses rather than adding new round trips).

**Constraints**: Constitution's "Backend Core non-processing endpoints MUST respond within 200ms (p95)" does not apply to `docuparse-process-ocr` (correctly modeled as a 30s-class processing endpoint, `timeout_ms=200_000` already exceeds the constitution's 30s OCR p95 target — a **pre-existing** deviation, not introduced by this feature; noted in Complexity Tracking for visibility, not re-litigated here). New job workers (`docuparse-notify-user`, `docuparse-log-failure`, `docuparse-preprocess-image`, `docuparse-reset-for-reprocessing`, `docuparse-archive-document`) are simple, sub-15s calls, consistent with the existing `docuparse-register-document`/`docuparse-validate-document` timeout class.

**Scale/Scope**: 5 files modified (`document.py`, `ocr.py`, `layout.py`, `main.py`, `_http.py` unchanged) + 1 file removed (`erp.py`) + up to 6 new worker modules/functions + 1 shared helper module (`_schema.py`) + 1 companion BPMN edit (gateway conditions + a small number of new service-task elements per `research.md`'s gap table) + backend-core additions (1 enum value, 2 model fields, 1-2 new endpoints) tracked as a dependency, not primary deliverable, of this plan. Also includes one small `backend-com` testing-tooling addition (T049): a `skip_manual_processing_flag` on the manual upload endpoint, so manually uploading a document to test the BPMN flow doesn't also trigger backend-core's separate non-BPMN auto-OCR pipeline on it — discovered as friction during quickstart validation (T048), not part of the core worker reconciliation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
|---|---|---|
| I. Code Quality — readability/type safety | New/changed worker functions follow the existing pattern (`ZeebeTaskRouter`, `async def`, typed params, `**kwargs` passthrough) already used across `document.py`/`ocr.py`/`layout.py`; each stays well under 50 lines. Shared `_schema.py` extraction (Decision 4) actively *reduces* duplication rather than adding it. | ✅ PASS |
| I. Code Quality — no dead code | `erp.py` is deleted (not just unregistered) per Decision 9. | ✅ PASS |
| I. Code Quality — complexity | No function in this plan exceeds a handful of branches; the complexity lives in the BPMN graph, not in any single worker function. | ✅ PASS |
| II. Testing Standards | **No `tests/` directory exists today under `camunda-workers/`** — a pre-existing gap this feature inherits. Constitution requires integration tests for "document processing pipelines" and ≥80% coverage for new code. This plan cannot claim compliance without task-phase work to add a `tests/` tree (unit tests per new/changed worker, mocked `httpx`). | ⚠️ GAP — tracked in Complexity Tracking, must produce tasks in `/speckit-tasks` |
| III. UX Consistency | `docuparse-notify-user` must produce the same human-readable, actionable message style as existing user-facing errors (constitution: "free of internal stack traces or raw exception text"); `rejectionReason` values feeding it should be short user-facing strings, not exception text — captured in `contracts/job-types.md`. | ✅ PASS (constraint documented) |
| IV. Performance Requirements | See Constraints above — pre-existing OCR timeout deviation noted, not worsened; new job types are lightweight. | ✅ PASS (pre-existing note only) |

**Gate result**: Proceed to Phase 0/1, with the Testing Standards gap explicitly carried into `/speckit-tasks` rather than silently ignored.

**Post-design re-check** (after `research.md`/`data-model.md`/`contracts/` were written):
No new violations surfaced during design. The design confirmed rather than worsened the two
flagged items: (1) the Testing Standards gap remains real and is now scoped to concrete
files (`tests/workers/test_*.py` per the Project Structure tree below); (2) the backend-core
touch points stayed minimal — one enum value, two nullable fields, one new endpoint — no
broader schema/API redesign was needed to satisfy the new gateways. No function introduced
by `contracts/job-types.md` exceeds the 50-line/complexity-10 Code Quality bar. Gate remains
✅ PASS with the same two tracked items in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
docs/specs/014-bpmn-worker-flow-update/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── job-types.md
│   └── gateway-conditions.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
docuparse-project/
├── bpmn/
│   ├── flow.bpmn                 # currently-deployed process (superseded by this feature)
│   └── flow_updated.bpmn         # target process; gains gateway conditions + a few new
│                                  # service-task elements per contracts/gateway-conditions.md
│                                  # and research.md's gap table (companion change, not a
│                                  # camunda-workers file, but required for the workers to
│                                  # be reachable at all)
│
├── camunda-workers/
│   ├── src/
│   │   ├── main.py               # MODIFY: drop erp router registration, add new routers
│   │   ├── config.py             # unchanged
│   │   └── workers/
│   │       ├── _http.py          # unchanged
│   │       ├── _schema.py        # NEW: shared LayoutConfig/SchemaConfig resolution
│   │       │                     #   (extracted from extraction.py, reused by layout.py)
│   │       ├── document.py       # MODIFY: register_document gains file_valid/rejection_reason;
│   │       │                     #   delete_document replaced by archive_document
│   │       ├── ocr.py            # MODIFY: process_ocr/reprocess_ocr gain ocr_readable
│   │       ├── layout.py         # MODIFY: classify_layout gains document_configured
│   │       ├── extraction.py     # MODIFY: use shared _schema.py helper; behavior unchanged
│   │       ├── validation.py     # unchanged (contract unchanged; now actually wired in BPMN)
│   │       ├── notification.py   # NEW: docuparse-notify-user
│   │       ├── observability.py  # NEW: docuparse-log-failure
│   │       ├── preprocessing.py  # NEW: docuparse-preprocess-image
│   │       ├── reprocessing.py   # NEW: docuparse-reset-for-reprocessing
│   │       └── erp.py            # DELETE (Decision 9)
│   │
│   └── tests/                    # NEW — currently missing (Constitution Check gap)
│       └── workers/
│           ├── test_document.py
│           ├── test_ocr.py
│           ├── test_layout.py
│           ├── test_notification.py
│           ├── test_observability.py
│           ├── test_preprocessing.py
│           ├── test_reprocessing.py
│           └── test_validation.py
│
└── backend-core/                 # DEPENDENCY, not primary deliverable of this plan —
    └── documents/                #   tracked so /speckit-tasks doesn't silently drop it:
        ├── models.py             #   MODIFY: Document.Status.ARCHIVED; file_valid,
        │                         #     rejection_reason, ocr_readable fields
        ├── views.py               #   MODIFY: validity check in ingestion path; readability
        │                         #     computation in OCR path; new archive endpoint
        └── urls.py                #   MODIFY: register archive endpoint route
```

**Structure Decision**: Single-project layout (Option 1) centered on
`docuparse-project/camunda-workers/`, matching the existing structure exactly — no new
top-level project/service is introduced. Two companion touch points are carried explicitly
in this plan rather than left implicit: `docuparse-project/bpmn/flow_updated.bpmn` (gateway
conditions + a handful of new elements, additive only) and `docuparse-project/backend-core/`
(the minimum model/endpoint additions the new gateways' signals depend on, per `research.md`
Decisions 2, 3, and 7). Both are scoped narrowly to exactly what `contracts/job-types.md` and
`contracts/gateway-conditions.md` require — no unrelated backend-core refactoring.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| No `tests/` directory exists yet for `camunda-workers` (Testing Standards gap) | This is a pre-existing gap in the codebase, not introduced by this feature — but this feature is the first to add non-trivial branching logic (retry counters, archive vs. delete, validate-document call sites) that genuinely needs regression protection. | Deferring test creation to "later" was rejected: constitution's Regression Policy and ≥80% coverage bar apply to new features, and this feature adds the highest-risk logic (money/compliance-adjacent document lifecycle transitions) the worker layer has seen yet. `/speckit-tasks` will include a task to scaffold `tests/` and cover each new/changed worker. |
| Companion changes reach into `backend-core` and `bpmn/flow_updated.bpmn`, beyond the literal `camunda-workers` folder named in the request | The new gateways (`Gateway_1hajqec`, `Gateway_0lylr3v`, `Gateway_01v609m`, plus the archive path) depend on signals (`file_valid`, `ocr_readable`, `documentConfigured`, soft-delete) that do not exist anywhere in the system today (confirmed via `research.md` backend-core research) — no worker-only change can produce them. | Scoping strictly to `camunda-workers/` and stubbing these signals with worker-local heuristics was considered (Decision 3's "Alternatives") and partially adopted as a phased interim for file-validity only; readability and soft-delete have no safe worker-local substitute since they require opening/inspecting file content or changing the authoritative lifecycle state, both of which belong in backend-core. |
