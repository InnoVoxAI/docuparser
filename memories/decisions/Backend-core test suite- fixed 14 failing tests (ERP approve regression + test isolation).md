---
title: 'Backend-core test suite: fixed 14 failing tests (ERP approve regression +
  test isolation)'
type: decision
permalink: docuparser/decisions/backend-core-test-suite-fixed-14-failing-tests-erp-approve-regression-test-isolation
tags:
- backend-core
- testing
- erp-integration
- multi-tenancy
---

## Context

On 2026-07-28, `run_script.sh ... pytest` on backend-core showed 14 failing tests. A prior commit (7833b12, "add platform roles and enforce permissions on config endpoints") had asserted these were a "baseline of 8 pre-existing failures (unrelated S3/event-bus/OCR flakiness)" — that framing was wrong. Investigation found real regressions plus a systemic test-isolation gap. All 143 tests pass after the fixes below.

## Findings & fixes

1. **ERP integration silently broken since ~June 3** (commit 447b419, "adjusting categorias approval pending and rejected"): `document_validation_view`'s APPROVED branch called `document.transition_to(Document.Status.APPROVED)` but the following line `publish_erp_integration_requested(document)` had been deleted. Approving a document via the API stopped requesting ERP integration and stopped exporting the approved JSON. Restored the call in `documents/views.py`.

2. **That exposed dead code**: `documents/services/erp_publisher.py` and `approved_exporter.py` still read `document.tenant.slug`. `Document` has had no `tenant` FK since the multi-tenancy schema migration (docs/specs/010-multi-tenancy-schemas) — tenant is now resolved from `connection.schema_name`. Because `publish_erp_integration_requested` had no caller since June, this was never exercised. Fixed both to derive `tenant_slug` from the connection schema (same pattern as `ocr_processor.py`) and thread it through as an explicit parameter instead of `document.tenant.slug`.

3. **Test-infra gotcha (root cause of most of the "8 pre-existing failures")**: `event_bus_from_env()` and `get_storage()` (in `docuparse-project/shared`) read `DOCUPARSE_EVENT_BUS` / `DOCUPARSE_STORAGE_BACKEND` straight from `os.environ`, not Django `settings`. The devcontainer's `.env` (loaded by `run_script.sh`) pins both to live services (`redis`, `s3`/MinIO). Tests that used `self.settings(DOCUPARSE_LOCAL_EVENT_DIR=...)` or `override_settings(DOCUPARSE_LOCAL_STORAGE_DIR=...)` alone had **no effect** — they silently hit the real shared Redis/MinIO instead of their local fixture, causing nondeterministic pass/fail depending on what garbage was already in those services from other runs/manual usage. Fix pattern (now used in `test_dlq_command.py`, the ERP/DLQ tests in `test_api.py`, and `test_document_delete_cleanup.py`): also `patch.dict(os.environ, {"DOCUPARSE_EVENT_BUS": "local"})` / `{"DOCUPARSE_STORAGE_BACKEND": "local", ...}` alongside the settings override. **Any new test that needs an isolated event bus or storage must patch these env vars, not just Django settings.**

4. **Stale tests, not bugs** — updated to match intentional, already-shipped behavior:
   - `seed_permissions` management command was folded into `seed_data` back in commit 4fb75f3 ("chore: doc env"); a test still called the deleted command by name.
   - A test patched `documents.views.start_document_ocr_thread`, which is no longer imported there (replaced by `submit_document_processing` during the 1f4fa0a lint-fix reorg). `start_document_ocr_thread` is now dead code in `ocr_processor.py`.
   - `ExtractionResult.fields` is synced to the `{value, confidence}` snapshot format by `field_versioning.save_manual_edit()` (feature 007-extracted-field-versioning) whenever corrected_fields are submitted, not the flat dict OCR/LangExtract write directly. A test still expected the flat shape.
   - `IntegrationSettings.id` defaults to a random `uuid4()`, not the app's `SETTINGS_SINGLETON_ID` — a test created a settings row without passing `id=SETTINGS_SINGLETON_ID`, so `erp_publisher._integration_settings()` never saw it and silently fell back to defaults.
   - The OCR-processing tests (`test_process_ocr_endpoint_*`, `test_reprocess_ocr_endpoint_*`) asserted the old "legacy_ocr" behavior where `process_document_ocr()` created an `ExtractionResult` directly from the OCR client's own fields. That was deliberately removed on 2026-05-18 (commit 3dccd3ee, "adjusting env"): OCR now only stores raw text and sets status `OCR_COMPLETED`; a separate `auto_extract_after_ocr()` step resolves a `SchemaConfig` (via `document.layout` → `LayoutConfig`, then text classifiers, then `document.document_type`) and calls `LangExtractClient` to populate `ExtractionResult`. There was **no test coverage at all** for `auto_extract_after_ocr()` before this fix. Rewrote the tests to seed a `LayoutConfig`/`SchemaConfig` and mock `LangExtractClient` to cover the current pipeline end-to-end, plus a no-schema-match case asserting the document stays at `OCR_COMPLETED` with no `ExtractionResult`.

## How to apply

- When adding new tests that need an isolated event bus or object storage, always pair the Django `settings` override with an `os.environ` patch for `DOCUPARSE_EVENT_BUS` / `DOCUPARSE_STORAGE_BACKEND` — settings alone won't isolate them in this devcontainer.
- Don't trust a commit message's claim that failing tests are "pre-existing/flaky" without checking git blame on the specific assertion — in this case the label was masking a real several-week-old regression in the approval → ERP integration flow.
- `Document` has no `tenant` FK; any new code needing the tenant slug from a `Document` instance should derive it from `connection.schema_name`, not `document.tenant`.
