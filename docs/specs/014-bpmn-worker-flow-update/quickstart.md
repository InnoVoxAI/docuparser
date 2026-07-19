# Quickstart: Validating the Updated DocuParse Worker Flow

**Feature**: `014-bpmn-worker-flow-update`

## Prerequisites

- Docker + Docker Compose (per constitution: all services containerized).
- From `docuparse-project/`: the `camunda` profile brings up Zeebe 8.6, Operate, Tasklist,
  and `camunda-workers`, alongside the existing `backend-core`/`backend-ocr`/etc. services.

## 1. Bring up the stack

```bash
cd docuparse-project
docker compose --profile camunda up -d --build
```

`camunda-workers` depends on `zeebe` (healthy) and `backend-core` (healthy) per
`docker-compose.yml`; Tasklist is reachable at `http://localhost:8082`, Operate for
visualizing running instances.

## 2. Deploy the updated process definition

```bash
docker compose exec camunda-workers python scripts/deploy_bpmn.py
```

This deploys every `*.bpmn` file under `docuparse-project/bpmn/` (mounted read-only into the
container) — including `flow_updated.bpmn` once it has the gateway conditions from
`contracts/gateway-conditions.md` added and replaces `flow.bpmn` as the deployed resource
for `docuparse-pipeline`.

## 3. Start a test process instance

```bash
docker compose exec camunda-workers python scripts/start_process.py \
  --tenant-id default \
  --document-id "$(python -c 'import uuid; print(uuid.uuid4())')" \
  --file-uri documents/default/<uuid>/original/<filename> \
  --content-type application/pdf \
  --channel email
```

## 4. Exercise each new path

| Scenario | How to trigger | Expect |
|---|---|---|
| Invalid file (US1) | Start with `--content-type application/x-msdownload` or a 0-byte `--size-bytes 0` | `Activity_0vx7jlw` notifies, `Activity_10ryy35` logs, process ends at `Event_1x9edwy` |
| Unreadable → auto-retry (US2) | Use a source document backend-core's OCR marks not-readable | `Activity_0dgit79` → `docuparse-process-ocr` loop runs up to 3x (`ocrRetryCount` visible in Operate variables view), then either recovers or ends at `Event_1w6k9fs` |
| Unconfigured document type (US3) | Classify a `layout`/`document_type` combo with no active `LayoutConfig` | Process reaches `Activity_1hafvqe` in Tasklist for an `operators` candidate to complete |
| High-confidence auto-approve (US4) | Use a document/schema combo known to extract >0.95 confidence | Process reaches `Event_15yo9c3` without ever creating a Tasklist item |
| Low-confidence → operator review (US5) | Use a document/schema combo below 0.95 confidence | `Task_HumanVal` appears in Tasklist (`operators` group); completing it with `approved=false` and `reprocessChoice="delete"` ends at `Event_07z8dpg` with `Document.status == ARCHIVED` |
| Observability (US6) | Any invalid-file or unreadable-after-retries run | A structured `docuparse-log-failure` log line (via `structlog`, basic logging only — no observability platform integration exists yet) appears in `camunda-workers`' container logs with `document_id`, `failure_reason`, `failure_step` |

## 5. Watch it in Operate

`http://localhost:8082` isn't Operate — Operate runs on the port mapped in
`docker-compose.yml` for the `operate` service (check `docker compose port operate 8080`).
Use it to confirm gateway routing matches `contracts/gateway-conditions.md` and that no
instance is stuck on an incident (e.g. `NO_MATCHING_CONDITION`, which would indicate a
missing default flow or a worker not returning an expected variable).

## 6. Run worker tests

No `tests/` directory exists yet under `camunda-workers/` (see `plan.md` Constitution
Check — this is a gap this feature's task list must close). Once added:

```bash
docker compose exec camunda-workers pytest
```
