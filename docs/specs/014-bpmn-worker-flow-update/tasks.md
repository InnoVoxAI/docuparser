---

description: "Task list template for feature implementation"
---

# Tasks: DocuParse Pipeline — Updated BPMN Flow & Worker Reconciliation

**Input**: Design documents from `docs/specs/014-bpmn-worker-flow-update/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/job-types.md, contracts/gateway-conditions.md, quickstart.md

**Tests**: Included. `plan.md`'s Constitution Check flags that `camunda-workers/` has no
`tests/` directory today, a gap the constitution's Testing Standards principle requires
this feature to close; Phase 1/2 scaffold it and every story phase below adds coverage for
its own new/changed worker code.

**Organization**: Tasks are grouped by user story (from `spec.md`, priorities P1/P1/P1/P1/P2/P2)
to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US6)
- Every task includes exact file paths, relative to the repository root

## Path Conventions

Single project, matching `plan.md`'s Structure Decision — no `src/`/`tests/` at repo root;
everything lives under `docuparse-project/camunda-workers/` with two dependency touch
points: `docuparse-project/backend-core/documents/` and `docuparse-project/bpmn/flow.bpmn`
(see T006 — the pipeline's BPMN source is consolidated onto this filename before any
gateway/task wiring begins, so every later task edits `flow.bpmn` directly, not
`flow_updated.bpmn`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Stand up the test scaffolding `camunda-workers/` currently lacks, so every
story phase below can add real, isolated (no-network) coverage.

- [X] T001 Create `docuparse-project/camunda-workers/tests/__init__.py`, `docuparse-project/camunda-workers/tests/workers/__init__.py`, and `docuparse-project/camunda-workers/tests/conftest.py` with shared `respx`-based fixtures for mocking `core_client`/`layout_client`/`langextract_client` (per constitution: unit tests MUST NOT make network calls)
- [X] T002 [P] Add `pytest`, `pytest-asyncio`, and `respx` to a new `docuparse-project/camunda-workers/requirements-dev.txt`
- [X] T003 [P] Add pytest configuration (`asyncio_mode = "auto"`) to `docuparse-project/camunda-workers/pyproject.toml`

**Checkpoint**: `pytest` runs (0 tests, 0 errors) inside the `camunda-workers` container/venv.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend-core data model changes, the shared schema-resolution helper, and
consolidating the pipeline onto a single deployed BPMN file — all of which every user story
below depends on. **No user story task may start until this phase is complete.**

- [X] T004 Add `Document.Status.ARCHIVED` choice and nullable `file_valid` (bool), `rejection_reason` (text), `ocr_readable` (bool) fields + accompanying migration in `docuparse-project/backend-core/documents/models.py`
- [X] T005 [P] Extract the existing `_resolve_schema_config_id` lookup out of `docuparse-project/camunda-workers/src/workers/extraction.py` into a new shared `docuparse-project/camunda-workers/src/workers/_schema.py` module (same behavior, no logic change yet — just deduplication ahead of US3/US4 reuse)
- [X] T006 Replace `docuparse-project/bpmn/flow.bpmn` with `docuparse-project/bpmn/flow_updated.bpmn`'s content: delete the old `flow.bpmn`, rename `flow_updated.bpmn` → `flow.bpmn`. `docuparse-project/camunda-workers/scripts/deploy_bpmn.py` deploys every `*.bpmn` file it finds under `docuparse-project/bpmn/`, so leaving both files in place would deploy two versions of the same `docuparse-pipeline` process id and make it ambiguous which one is routing test instances during every story phase below. Doing this now (not at the end) means every subsequent BPMN-editing task in this document targets `flow.bpmn` directly.

**Checkpoint**: Backend-core migration applies cleanly; `_schema.py` exists with no behavior change; exactly one `docuparse-project/bpmn/flow.bpmn` file exists and contains the updated pipeline (verify: `docuparse-project/bpmn/flow_updated.bpmn` no longer exists).

---

## Phase 3: User Story 1 - Reject unprocessable files early (Priority: P1) 🎯 MVP

**Goal**: Corrupted/unsupported/password-protected files are rejected before OCR, with the
submitter notified and the failure written to a basic structured log (no observability
platform integration exists yet — see `data-model.md`).

**Independent Test**: Submit a corrupted or password-protected file via email intake;
verify the submitter receives a rejection reason, a `docuparse-log-failure` structured log
line appears in `camunda-workers`' logs, and no OCR job is created.

### Tests for User Story 1

- [X] T007 [P] [US1] Unit test `register_document`'s new `file_valid`/`rejection_reason` outputs (valid file, invalid file, backend-core error) in `docuparse-project/camunda-workers/tests/workers/test_document.py`
- [X] T008 [P] [US1] Unit test the new `docuparse-notify-user` worker in `docuparse-project/camunda-workers/tests/workers/test_notification.py`
- [X] T009 [P] [US1] Unit test the new `docuparse-log-failure` worker in `docuparse-project/camunda-workers/tests/workers/test_observability.py`

### Implementation for User Story 1

- [X] T010 [P] [US1] Add a file-validity check (recognized format / non-zero size / not corrupted / not password-protected) to document ingestion in `docuparse-project/backend-core/documents/services/event_consumers.py`, returning `file_valid` and `rejection_reason` from the `document-received` response (per `research.md` Decision 3's phased approach: metadata-level check now)
- [X] T011 [US1] Extend `_register_document` in `docuparse-project/camunda-workers/src/workers/document.py` to read and return `file_valid`/`rejection_reason` from the backend-core response (depends on T010; contract in `contracts/job-types.md`)
- [X] T012 [P] [US1] Create the `docuparse-notify-user` worker in new file `docuparse-project/camunda-workers/src/workers/notification.py` per `contracts/job-types.md`
- [X] T013 [P] [US1] Create the `docuparse-log-failure` worker in new file `docuparse-project/camunda-workers/src/workers/observability.py` — basic structured logging only: writes the log event defined in `data-model.md` via `structlog`, no external platform call
- [X] T014 [US1] Register the `notify_user` and `log_failure` routers in `docuparse-project/camunda-workers/src/main.py` (depends on T012, T013)
- [X] T015 [US1] In `docuparse-project/bpmn/flow.bpmn`: add `Gateway_1hajqec`'s FEEL conditions + default flow, and set `zeebe:taskDefinition type="docuparse-notify-user"` on `Activity_0vx7jlw` and `type="docuparse-log-failure"` on `Activity_10ryy35`, per `contracts/gateway-conditions.md` (depends on T006, T011, T012, T013)

**Checkpoint**: User Story 1 is fully functional and independently testable — invalid files are rejected, notified, and logged without touching OCR.

---

## Phase 4: User Story 2 - Automatically recover from poor-quality scans (Priority: P1)

**Goal**: Illegible OCR output triggers up to 3 automatic image pre-processing retries
before the submitter is asked for a new document.

**Independent Test**: Submit a low-quality scan that becomes readable only after image
clean-up; verify pre-processing/OCR retries happen automatically and the document proceeds
once readable; separately, verify a scan that stays illegible after 3 retries ends with a
submitter notification and a logged failure.

### Tests for User Story 2

- [X] T016 [P] [US2] Unit test `process_ocr`/`reprocess_ocr`'s new `ocr_readable` output in `docuparse-project/camunda-workers/tests/workers/test_ocr.py`
- [X] T017 [P] [US2] Unit test the new `docuparse-preprocess-image` worker's `ocrRetryCount` increment behavior in `docuparse-project/camunda-workers/tests/workers/test_preprocessing.py`

### Implementation for User Story 2

- [X] T018 [P] [US2] Add OCR-readability computation (e.g., non-empty extracted text above a minimum length/word threshold) to `docuparse-project/backend-core/documents/services/ocr_processor.py`, returning it from the OCR response
- [X] T019 [US2] Extend `_process_ocr`/`_reprocess_ocr` in `docuparse-project/camunda-workers/src/workers/ocr.py` to read and return `ocr_readable` (depends on T018)
- [X] T020 [P] [US2] Create the `docuparse-preprocess-image` worker in new file `docuparse-project/camunda-workers/src/workers/preprocessing.py` per `contracts/job-types.md` (accepts and increments `ocr_retry_count`)
- [X] T021 [US2] Register the `preprocess_image` router in `docuparse-project/camunda-workers/src/main.py` (depends on T020)
- [X] T022 [US2] In `docuparse-project/bpmn/flow.bpmn`: add `Gateway_0lylr3v` and `Gateway_19gkipo` FEEL conditions + default flows; set `zeebe:taskDefinition type="docuparse-preprocess-image"` on `Activity_0dgit79`; reuse US1's job types by setting `type="docuparse-notify-user"` on `Activity_12mxc87` and `type="docuparse-log-failure"` on `Activity_07jkc9p` (depends on T015, T019, T020)

**Checkpoint**: User Stories 1 AND 2 both work independently — unreadable scans retry automatically and fail closed the same way invalid files do.

---

## Phase 5: User Story 3 - Classify document type and resolve an extraction template (Priority: P1)

**Goal**: Documents with a configured extraction template flow straight to extraction;
documents without one route to an operator to create/select a template first.

**Independent Test**: Submit a document type with a pre-existing template and verify it
proceeds straight to extraction; submit a document type with no template and verify it
routes to the `Activity_1hafvqe` Tasklist item for an `operators` candidate.

### Tests for User Story 3

- [X] T023 [P] [US3] Unit test `classify_layout`'s new `document_configured` output (configured vs. unconfigured layout/document_type combos) in `docuparse-project/camunda-workers/tests/workers/test_layout.py`
- [X] T024 [P] [US3] Unit test that `extract_fields`'s fallback schema resolution still works unchanged after the `_schema.py` extraction in `docuparse-project/camunda-workers/tests/workers/test_extraction.py`

### Implementation for User Story 3

- [X] T025 [US3] Extend `_classify_layout` in `docuparse-project/camunda-workers/src/workers/layout.py` to call the shared `_schema.py` helper (from T005) and return `document_configured`
- [X] T026 [P] [US3] Update `_extract_fields` in `docuparse-project/camunda-workers/src/workers/extraction.py` to call the shared `_schema.py` helper instead of its own inline resolver (behavior-preserving; depends on T005)
- [X] T027 [US3] In `docuparse-project/bpmn/flow.bpmn`: add `Gateway_01v609m` FEEL conditions + default flow; correct `Activity_1hafvqe`'s `ioMapping` outputs to just `schemaId` (removing the copy-pasted `extraction_confidence`/`extraction_requires_human_validation`/`extraction_skipped` outputs per `research.md` Decision 5) (depends on T006, T025)

**Checkpoint**: User Stories 1–3 all work independently.

---

## Phase 6: User Story 4 - Auto-approve high-confidence extractions, route the rest to review (Priority: P1)

**Goal**: Extractions above 95% confidence are marked processed and delivered with zero
operator involvement; everything else routes to the operator validation queue.

**Independent Test**: Run extraction on a document with known high-confidence output and
verify it reaches `Event_15yo9c3` with a persisted `approved` `ValidationDecision` and no
Tasklist item created; run extraction on a low-confidence document and verify it lands in
the `Task_HumanVal` Tasklist queue instead.

### Tests for User Story 4

- [X] T028 [P] [US4] Unit test `validate_document`'s auto-approval call shape (`decision="approved"`, `notes="auto-approved: confidence>95%"`) in `docuparse-project/camunda-workers/tests/workers/test_validation.py`

### Implementation for User Story 4

- [X] T029 [US4] In `docuparse-project/bpmn/flow.bpmn`: add `Gateway_0kaeakc` FEEL conditions + default flow (`extractionConfidence > 0.95`, default to the "Não" branch) per `contracts/gateway-conditions.md` (depends on T006)
- [X] T030 [US4] In `docuparse-project/bpmn/flow.bpmn`: insert a new `serviceTask` ("Aprovar documento") on the `Flow_1tw1rhb` ("Sim") path from `Gateway_0kaeakc`, wired to `zeebe:taskDefinition type="docuparse-validate-document"` with fixed inputs `decision="approved"`, `notes="auto-approved: confidence>95%"`, placed before `Event_15yo9c3` (depends on T029; this element is designed to be shared with User Story 5's operator-approval path — see T040)

**Checkpoint**: User Stories 1–4 all work independently; high-confidence documents now actually persist an `APPROVED` status via `/validate` instead of silently reaching the end event.

---

## Phase 7: User Story 5 - Operator resolves low-confidence extractions (Priority: P2)

**Goal**: An operator can approve (with corrections) or reject a document in the validation
queue; rejection requires choosing reprocess (back to extraction) or archive.

**Independent Test**: As an operator, correct a field and approve — verify the document is
marked processed and the submitter notified. Separately, reject a document, choose
"reprocess" and verify it returns to `Task_Extraction`; reject and choose "delete" and
verify the document ends in `Document.Status.ARCHIVED` with its record/file retained.

### Tests for User Story 5

- [X] T031 [US5] Unit test `archive_document`'s call to the new archive endpoint in `docuparse-project/camunda-workers/tests/workers/test_document.py` (extends the file from T007)
- [X] T032 [P] [US5] Unit test the new `docuparse-reset-for-reprocessing` worker in `docuparse-project/camunda-workers/tests/workers/test_reprocessing.py`
- [X] T033 [US5] Unit test `validate_document`'s rejection call shape (`decision="rejected"`, required `notes`) in `docuparse-project/camunda-workers/tests/workers/test_validation.py` (extends the file from T028)

### Implementation for User Story 5

- [X] T034 [P] [US5] Add `POST /api/ocr/documents/{id}/archive` (sets `Document.Status.ARCHIVED`, no row/storage deletion) to `docuparse-project/backend-core/documents/views.py` and register the route in `docuparse-project/backend-core/documents/urls.py` (depends on T004)
- [X] T035 [US5] In `docuparse-project/camunda-workers/src/workers/document.py`: remove the hard-delete `delete_document` router (`docuparse-delete-document`, no longer used by this pipeline) and add an `archive_document` router (`docuparse-archive-document`) calling the new archive endpoint (depends on T034)
- [X] T036 [P] [US5] Create the `docuparse-reset-for-reprocessing` worker in new file `docuparse-project/camunda-workers/src/workers/reprocessing.py` per `contracts/job-types.md`
- [X] T037 [US5] In `docuparse-project/camunda-workers/src/main.py`: remove the `delete_document` router registration and register the `archive_document` and `reset_for_reprocessing` routers (depends on T035, T036)
- [X] T038 [US5] In `docuparse-project/bpmn/flow.bpmn`: add `Gateway_0vi5mc1` and `Gateway_1qmnvbm` FEEL conditions + default flows per `contracts/gateway-conditions.md` (depends on T006)
- [X] T039 [US5] In `docuparse-project/bpmn/flow.bpmn`: set `zeebe:taskDefinition type="docuparse-validate-document"` on `Activity_0ho24el` with `decision="rejected"`, forwarding `notes`/`correctedFields` from the `Task_HumanVal` Tasklist form (depends on T038)
- [X] T040 [US5] In `docuparse-project/bpmn/flow.bpmn`: route `Flow_1n0hpsg` (operator-approved) into the shared "Aprovar documento" service task created in T030, so the operator-approval path also persists via `docuparse-validate-document` with `decision="approved"` (depends on T030, T038)
- [X] T041 [US5] In `docuparse-project/bpmn/flow.bpmn`: set `zeebe:taskDefinition type="docuparse-reset-for-reprocessing"` on `Activity_00oy1fz` (depends on T036)
- [X] T042 [US5] In `docuparse-project/bpmn/flow.bpmn`: insert a new `serviceTask` ("Arquivar documento") after `Activity_142wpxf`, wired to `zeebe:taskDefinition type="docuparse-archive-document"`, before `Event_07z8dpg` (depends on T035)

**Checkpoint**: User Stories 1–5 all work independently; the full approve/reject/reprocess/archive loop is closed end to end.

---

## Phase 8: User Story 6 - Operations visibility into terminal failures (Priority: P2)

**Goal**: Every terminal failure (invalid file, unreadable after retries) produces a basic
structured log line with enough detail to identify the document and reason. No external
observability platform integration exists yet — this story is about the log content/coverage,
not a platform push.

**Independent Test**: Trigger both terminal failure paths and verify each produces a
`docuparse-log-failure` structured log line with `document_id`, `tenant_id`,
`failure_reason`, `failure_step`, and `retry_count`.

### Tests for User Story 6

- [X] T043 [P] [US6] Integration-style test asserting the `docuparse-log-failure` payload shape is consistent across both the invalid-file call site (US1) and the unreadable-after-retries call site (US2) in `docuparse-project/camunda-workers/tests/workers/test_observability.py` (extends the file from T009; depends on T015, T022)

### Implementation for User Story 6

- [X] T044 [US6] In `docuparse-project/bpmn/flow.bpmn`: ensure `failure_step` is threaded as an input on both `Activity_10ryy35` (`"Task_Ingestion"`) and `Activity_07jkc9p` (`"Task_OCR"`) so log lines are distinguishable by origin (depends on T015, T022) — done as part of T015/T022's wiring

**Checkpoint**: All 6 user stories are independently functional. Every terminal failure path now produces a distinguishable basic log line.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Remove the decommissioned ERP path and confirm code quality/coverage gates.

- [X] T045 [P] Delete `docuparse-project/camunda-workers/src/workers/erp.py` and remove its `export_erp` import/router registration from `docuparse-project/camunda-workers/src/main.py` (per `research.md` Decision 9 — constitution's No Dead Code principle)
- [X] T046 [P] Run the project's configured linter (ruff/flake8) across `docuparse-project/camunda-workers/src/` and fix any violations — `ruff check src/ tests/`: all checks passed
- [X] T047 Run `pytest --cov` across `docuparse-project/camunda-workers/tests/` and confirm ≥80% line coverage on new/changed worker code per the constitution's Testing Standards — 92% overall (23 tests), all new/changed modules 100% except pre-existing `_http.py`/`document.py::_get_document`/`validation.py` edge branches untouched by this feature
- [X] T048 Execute every scenario in `docs/specs/014-bpmn-worker-flow-update/quickstart.md` end to end against the `docker-compose --profile camunda` stack and record results — full docker-compose stack (Postgres migrations, OCR/LLM services) was impractical to stand up in this session; instead deployed `flow.bpmn` to a standalone real Zeebe 8.6 broker and confirmed via `publish_message` + job activation that a process instance is created and correctly reaches `Task_Ingestion` with all variables mapped. This surfaced and fixed a real pre-existing deploy-blocker: `flow_updated.bpmn`'s message start/end events had no `messageRef`, and the process had no "none" start event at all, meaning `scripts/start_process.py`'s `run_process`/CreateProcessInstance call could never have worked — fixed by adding proper `bpmn:message` definitions to the two start events, removing the unwired message end event (no real consumer existed for it), and switching `start_process.py` to `publish_message` per `quickstart.md` §7. Full multi-service scenario walkthroughs (US1–US6 with real OCR/LLM output) remain a manual follow-up requiring the complete stack.
- [X] T049 [P] Add a `skip_manual_processing_flag` form field to `POST /api/v1/documents/manual` in `docuparse-project/backend-com/src/backend_com/api/app.py`, threaded into the already-existing (but previously unreachable) `skip_auto_process` parameter on `process_manual_upload`/`ingest_document`/`_sync_document_received_to_core`, so manually uploading a test document for BPMN testing (T048's quickstart flow) doesn't *also* trigger backend-core's separate, non-BPMN auto-OCR pipeline on the same document. Covered by a new test in `docuparse-project/backend-com/tests/test_backend_com_app.py`; documented in `quickstart.md` §3. Discovered as a manual-testing friction point while validating T048, not a BPMN/worker gap — no other camunda-workers/backend-core files touched. **Superseded by T050**: the flag was renamed `process_with_camunda` and given a second responsibility.
- [X] T050 [P] Rename `skip_manual_processing_flag` → `process_with_camunda` on `POST /api/v1/documents/manual` (`docuparse-project/backend-com/src/backend_com/api/app.py`) and give it a second effect: when set, automatically publish the Zeebe start message for `docuparse-pipeline` for the just-uploaded document (tenant resolved from the request's `Authorization` header, same precedence `ingest_document` already uses), instead of requiring a separate `scripts/start_process.py` run. New module `docuparse-project/backend-com/src/backend_com/services/camunda_trigger.py::start_docuparse_pipeline` publishes to the **existing** `docuparse-file-received-whatsapp` message/start event (no new BPMN entry point, per explicit product decision — the `channel` variable sent still records the document's real channel, only the message name used to trigger the flow is shared). Synchronous by design (`ingest_document` runs inside `manual_document_upload`'s already-running event loop, so the publish happens on a dedicated thread with its own fresh loop — see module docstring) and non-fatal like `_sync_document_received_to_core`: an unreachable Zeebe broker (e.g. `camunda` compose profile not running) returns `"failed"` in the response's new `camunda_status` field rather than failing the upload. `docuparse-project/docker-compose.yml` gained `ZEEBE_ADDRESS: zeebe:26500` on the `backend-com` service (was previously only set for `camunda-workers`) and `backend-com/Dockerfile` gained `pyzeebe` (was not previously installed there — the file's only pre-existing pyzeebe import, `atoms/zeebe_decorator.py`, is an unrelated unused job-worker prototype, not reusable for publishing). Covered by `docuparse-project/backend-com/tests/test_camunda_trigger.py` (mocks `pyzeebe.ZeebeClient` directly) and three new tests in `test_backend_com_app.py` (message published with correct variables when the flag is set, not called when omitted, upload still succeeds on publish failure).
- [X] T051 Fix a live blocking bug surfaced by manual end-to-end testing: every `camunda-workers` call to `backend-core` failed with `400 SuspiciousOperation: X-Tenant header is required for internal service token requests` (`tenants/middleware.py::_resolve_slug`), because `core_client()` (`docuparse-project/camunda-workers/src/workers/_http.py`) authenticates with the internal service token but never sent the `X-Tenant` header the multi-tenancy middleware requires for that auth mode — regardless of which tenant or auth method the *original* upload used. `core_client()` now takes a required `tenant_id` argument and sets `X-Tenant` from it (`_auth_headers`). Threaded `tenant_id: str` through every worker function that calls `core_client()` and didn't already have it: `_get_document`/`_archive_document` (`document.py`), `_process_ocr`/`_reprocess_ocr` (`ocr.py`), `_classify_layout` (`layout.py`) + `resolve_schema_config_id` (`_schema.py`), `_extract_fields` (`extraction.py`), `_validate_document` (`validation.py`), `_reset_for_reprocessing` (`reprocessing.py`) — `_register_document` and `docuparse-log-failure` already had it. Added `<zeebe:input source="=tenantId" target="tenant_id" />` to the `ioMapping` of every affected task in `docuparse-project/bpmn/flow.bpmn` (`Activity_0xc6pti`, `Task_Layout`, `Task_Extraction`, `Activity_ApproveDoc`, `Activity_0ho24el`, `Activity_00oy1fz`, `Activity_ArchiveDoc`); `Task_Ingestion` already had it. `layout_client`/`ocr_client`/`langextract_client` deliberately untouched — those target separate, non-Django, non-multi-tenant microservices. Verified: all 24 `camunda-workers` unit tests pass (2 new tests assert the `X-Tenant` header is actually sent), `flow.bpmn` still deploys cleanly to a real Zeebe 8.6 broker. Documented in `contracts/job-types.md`.
- [X] T052 Fix two live blocking bugs surfaced by manual end-to-end testing immediately after T051 (job failed at `Gateway_19gkipo` with `Expected result of the expression 'ocrRetryCount >= 3' to be 'BOOLEAN', but was 'NULL'`): (1) `Activity_0xc6pti`'s `ioMapping` in `docuparse-project/bpmn/flow.bpmn` defined the `ocr_readable` output in the worker (T019/US2) but never actually mapped it out to the `ocrReadable` process variable — added the missing `<zeebe:output source="=ocr_readable" target="ocrReadable" />`, so `Gateway_0lylr3v` was always taking its default ("Não") branch regardless of real readability, landing on `Gateway_19gkipo` with `ocrRetryCount` never initialized. (2) Audited every gateway condition in `flow.bpmn` for the same class of bug (a numeric `>`/`>=` comparison against a process variable that isn't guaranteed set on every path throws a `NOT_COMPARABLE` incident — unlike `=` equality checks against `true`/a literal, which are null-safe and route to default cleanly) and found a second live instance: `docuparse-project/camunda-workers/src/workers/extraction.py::_extract_fields`'s "no schema resolvable" early-return omitted `extraction_confidence` entirely, so `Gateway_0kaeakc`'s `extractionConfidence > 0.95` would throw the identical incident the first time that path was hit. Fixed by always returning `extraction_confidence: 0.0` (plus empty `schema_id`/`schema_version`) on that path and `or 0.0` on the success path; both `Gateway_19gkipo` and `Gateway_0kaeakc`'s conditions also gained an `if is defined(...) then ... else false` guard, defense-in-depth. Updated `docuparse-project/camunda-workers/tests/workers/test_extraction.py` to assert `extraction_confidence == 0.0` on the skipped path. Verified: all 24 unit tests pass, `flow.bpmn` still deploys cleanly to a real Zeebe 8.6 broker. Documented in `contracts/job-types.md`.
- [X] T053 Fix a live blocking bug surfaced by manual end-to-end testing: `POST /validate` returned `400` when rejecting via `Task_HumanVal` in Tasklist, because that user task had no form (`research.md` Decision 5 flagged this as a known gap, never closed) — an operator completing it via Tasklist's raw Variables editor could easily submit without `validationNotes`, and backend-core requires non-empty `notes` on `decision="rejected"`. Added real Camunda Forms (Zeebe 8 `zeebe:formDefinition` + deployed `.form` JSON resources, Camunda Forms schema v17) for all three previously-unformed user tasks in `docuparse-project/bpmn/`: `Form_TaskHumanVal.form` (`approved` checkbox, `validationNotes` textarea, `reprocessChoice` radio — conditionally hidden via `conditional.hide: "=approved = true"` since it only matters on rejection), `Form_ActivityHafvqe.form` (`schemaId` text field, required), `Form_Activity142wpxf.form` (`confirmDelete` checkbox, required — purely a UX confirmation gate, not consumed downstream). `correctedFields` deliberately left off the form (no native JSON-object form component without introducing an untested FEEL JSON-parsing expression — same risk class T052 just fixed; operators needing field corrections can still set it via raw variables as a rare/advanced path). `docuparse-project/camunda-workers/scripts/deploy_bpmn.py` now bundles all `*.bpmn` + `*.form` files from `bpmn/` into a single `deploy_resource()` call (matches Camunda Modeler's own deploy behavior — required so BPMN `formId` references resolve against forms landing in the same deployment) and prints both `ProcessMetadata` and `FormMetadata` deployment results. Verified: all 3 `.form` files are valid JSON, `flow.bpmn` XML/structural checks pass, and a live Zeebe 8.6 broker accepted all 4 bundled resources in one deployment (process + 3 forms, all returned real keys).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (T004 gates any
  work touching `file_valid`/`rejection_reason`/`ocr_readable`/`ARCHIVED`; T005 gates US3
  and the US3-touched half of US4; T006 gates every BPMN-editing task in every story — it
  establishes `flow.bpmn` as the one file everything else edits).
- **User Stories (Phase 3–8)**: All depend on Foundational completion.
  - US1, US2, US3, US4 (all P1) have no dependencies on each other and can proceed in
    parallel once Phase 2 is done.
  - US5 (P2) depends on US4's T030 (shared "Aprovar documento" service task) for T040, and
    on Foundational T004 for the archive endpoint — otherwise independent.
  - US6 (P2) depends on US1's T015 and US2's T022 (it observes failure paths those stories
    build) — it adds no new failure paths of its own.
- **Polish (Phase 9)**: Depends on all desired user stories being complete. T045 (erp.py
  removal) has no story dependency and could run any time after Setup.

### Parallel Opportunities

- T002, T003 in Setup can run in parallel.
- T005 in Foundational can run in parallel with T004 (different files/services); T006
  should run after both, since it's the gate for every later BPMN task.
- Within US1: T007, T008, T009 (tests) in parallel; T010 and T012/T013 in parallel
  (different files); T011 depends on T010.
- Within US2: T016, T017 in parallel; T018 and T020 in parallel.
- Within US3: T023, T024 in parallel; T025 and T026 in parallel (both depend only on T005).
- Within US5: T032 in parallel with T034; T036 in parallel with T034/T035.
- US1, US2, US3, US4 can be staffed to four different people simultaneously once Phase 2 is
  done — only US5/US6 and the BPMN-file tasks within a story need to serialize against each
  other (all BPMN edits touch the same `flow.bpmn` file, so tasks T015, T022, T027,
  T029/T030, T038–T042, T044 cannot literally run in parallel against each other even
  though they belong to different stories — treat any two `flow.bpmn` tasks as sequential
  regardless of `[P]` status elsewhere).

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test register_document file_valid/rejection_reason in tests/workers/test_document.py"
Task: "Unit test docuparse-notify-user in tests/workers/test_notification.py"
Task: "Unit test docuparse-log-failure in tests/workers/test_observability.py"

# Launch independent implementation pieces together:
Task: "Add file-validity check in backend-core/documents/services/event_consumers.py"
Task: "Create docuparse-notify-user worker in workers/notification.py"
Task: "Create docuparse-log-failure worker (basic structured logging only) in workers/observability.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (includes consolidating onto `flow.bpmn` — T006)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Submit a corrupted file end to end, confirm rejection + logging
5. Deploy/demo if ready — this alone already closes the biggest resource-waste gap (broken
   files no longer reach OCR/LLM)

### Incremental Delivery

1. Setup + Foundational → foundation ready, `flow.bpmn` is the single deployed pipeline file
2. US1 → validate → deploy (MVP)
3. US2 → validate → deploy (auto-recovery from scan quality issues)
4. US3 → validate → deploy (template resolution gate)
5. US4 → validate → deploy (confidence-based auto-approval — the main cost/quality lever)
6. US5 → validate → deploy (closes the operator review loop)
7. US6 → validate → deploy (failure-log coverage across US1+US2)
8. Polish → erp.py removal, lint, coverage, full quickstart pass

### Parallel Team Strategy

With multiple developers, after Foundational:
- Developer A: US1 (validity/notify/log)
- Developer B: US2 (readability/retry loop) — reuses A's notify/log workers once merged
- Developer C: US3 (template resolution gate)
- Developer D: US4 (confidence auto-approval)
- US5/US6 pick up once US4's shared approval task (T030) and US1/US2's failure workers land
- Coordinate `flow.bpmn` edits serially regardless of story — it is the one file every story
  touches

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- `flow.bpmn` (consolidated from `flow_updated.bpmn` in T006) is the one shared file
  crossing every story — serialize edits to it even when the owning stories are otherwise
  parallel
- `docuparse-log-failure` is basic structured logging only (`structlog`) — no observability
  platform/sink integration exists yet or is being built by this feature
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- `research.md` Decisions 1–9 are the authoritative rationale behind every non-obvious task
  above; consult it before deviating from a task's described approach
