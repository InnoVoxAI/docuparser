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

## 3. Upload a real document — this starts the process instance automatically

`backend-com`'s manual upload endpoint (port 8070) both stores the file *and*, when
`process_with_camunda=true`, publishes the Zeebe start message for `docuparse-pipeline`
for the tenant resolved from your `Authorization` header — no separate
`start_process.py` call needed:

```bash
curl -s -X POST http://localhost:8070/api/v1/documents/manual \
  -F "file=@docuparse-project/tests/docs/nf/pdf/N.F JADI MELO.pdf" \
  -F "tenant_id=tenant-demo" \
  -F "process_with_camunda=true" | python3 -m json.tool
# {"document_id": "...", "file_uri": "...", ..., "core_sync_status": "...", "camunda_status": "published"}
```

`camunda_status` tells you what happened: `"published"` means the message went out
successfully; `"failed"` means Zeebe wasn't reachable (e.g. you brought the stack up
without `--profile camunda`, or `ZEEBE_ADDRESS` isn't set for `backend-com`) — the
upload itself still succeeds either way, this is best-effort.
`"not_requested"` means the flag was omitted.

No auth header is needed above in local dev unless `DOCUPARSE_INTERNAL_SERVICE_TOKEN`
is set in `.env`, in which case add `-H "Authorization: Bearer <that value>"` to the
`curl` call. Sample PDFs already in the repo for exercising different document types:
`docuparse-project/tests/docs/nf/pdf/*.pdf`, `docuparser/scripts/tests/pdf/boleto
scaneado image.pdf`, `docuparser/scripts/tests/pdf/Recibo  digitalizado com manuscrito
assinatura.pdf`.

**Lower-level alternative**: `start_process.py` only *tells* the pipeline a file exists
at a given URI — it doesn't upload anything itself. If you need to start a process
instance for a document you registered some other way (or want explicit control over
every variable), upload with `process_with_camunda` omitted, then:

```bash
docker compose exec camunda-workers python scripts/start_process.py \
  --tenant-id tenant-demo \
  --document-id "<document_id from the upload response>" \
  --file-uri "<file_uri from the upload response>" \
  --original-filename "N.F JADI MELO.pdf" \
  --content-type application/pdf \
  --size-bytes <size_bytes from the upload response> \
  --sha256 "<sha256 from the upload response>" \
  --channel email
```

## 4. Exercise each new path

| Scenario | How to trigger | Expect |
|---|---|---|
| Invalid file (US1) | Start with `--content-type application/x-msdownload` or a 0-byte `--size-bytes 0` | `Activity_0vx7jlw` notifies, `Activity_10ryy35` logs, process ends at `Event_1x9edwy` |
| Unreadable → auto-retry (US2) | Use a source document backend-core's OCR marks not-readable | `Activity_0dgit79` → `docuparse-process-ocr` loop runs up to 3x (`ocrRetryCount` visible in Operate variables view), then either recovers or ends at `Event_1w6k9fs` |
| Unconfigured document type (US3) | Classify a `layout`/`document_type` combo with no active `LayoutConfig` | Process reaches `Activity_1hafvqe` in Tasklist for an `operators` candidate to complete — renders a form (`schemaId` field, required) |
| High-confidence auto-approve (US4) | Use a document/schema combo known to extract >0.95 confidence | Process reaches `Event_15yo9c3` without ever creating a Tasklist item |
| Low-confidence → operator review (US5) | Use a document/schema combo below 0.95 confidence | `Task_HumanVal` appears in Tasklist (`operators` group), rendering a form (`approved` checkbox, `validationNotes`, `reprocessChoice` — the last shown only when rejecting). Complete it unchecked with `validationNotes` filled in and `reprocessChoice="delete"` selected → ends at `Event_07z8dpg` via `Activity_142wpxf`'s own confirmation form, `Document.status == ARCHIVED` |
| Observability (US6) | Any invalid-file or unreadable-after-retries run | A structured `docuparse-log-failure` log line (via `structlog`, basic logging only — no observability platform integration exists yet) appears in `camunda-workers`' container logs with `document_id`, `failure_reason`, `failure_step` |

## 5. Watch it in Operate

`http://localhost:8082` isn't Operate — Operate runs on the port mapped in
`docker-compose.yml` for the `operate` service (check `docker compose port operate 8080`).
Use it to confirm gateway routing matches `contracts/gateway-conditions.md` and that no
instance is stuck on an incident (e.g. `NO_MATCHING_CONDITION`, which would indicate a
missing default flow or a worker not returning an expected variable).

## 6. Run worker tests

`camunda-workers/Dockerfile.test` builds a test-runner image with
`requirements-dev.txt` (pytest, pytest-asyncio, respx, pytest-cov, ruff)
pre-installed, separate from the production `Dockerfile`:

```bash
cd docuparse-project/camunda-workers
docker build -f Dockerfile.test -t docuparse-camunda-workers:test .
docker run --rm -v "$(pwd)":/app -w /app docuparse-camunda-workers:test pytest --cov=src/workers --cov-report=term-missing
docker run --rm -v "$(pwd)":/app -w /app docuparse-camunda-workers:test ruff check src/ tests/
```

All worker HTTP calls are mocked via `respx` (see `tests/conftest.py`) — no
network access or running services required for this step.

## 7. Verify the BPMN deploys against a real Zeebe broker

`docuparse-pipeline` has only message start events (`docuparse-file-received-email`,
`docuparse-file-received-whatsapp` — no "none" start event), so it can only be
started via `client.publish_message`, not `client.run_process`/CreateProcessInstance.
`scripts/start_process.py` already does this; a standalone broker is enough to smoke-test
deployment and routing without the rest of the stack:

```bash
docker network create docuparse-smoke
docker run -d --name zeebe-smoke --network docuparse-smoke \
  -e ZEEBE_BROKER_NETWORK_HOST=0.0.0.0 -p 26500:26500 camunda/zeebe:8.6.0
# wait for the broker to be healthy, then:
docker run --rm --network docuparse-smoke \
  -v "$(pwd)":/app -w /app -v "$(pwd)/../bpmn":/app/bpmn:ro \
  -e ZEEBE_ADDRESS=zeebe-smoke:26500 \
  docuparse-camunda-workers:test python scripts/deploy_bpmn.py
docker run --rm --network docuparse-smoke \
  -v "$(pwd)":/app -w /app -e ZEEBE_ADDRESS=zeebe-smoke:26500 \
  docuparse-camunda-workers:test python scripts/start_process.py \
  --tenant-id default --document-id "$(python3 -c 'import uuid; print(uuid.uuid4())')" \
  --channel email --file-uri documents/default/x/original/x.pdf
docker rm -f zeebe-smoke && docker network rm docuparse-smoke
```
