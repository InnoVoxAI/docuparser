# Shared development adapters

Initial foundation decisions:

- Event bus: Redis Streams for the integrated environment. The local `LocalJsonlEventBus` adapter is intentionally tiny and is used only for deterministic contract and smoke tests.
- Storage: MinIO/S3-compatible object storage for the integrated environment. The local `LocalStorage` adapter preserves the same object-key convention for unit tests and local scripts.

Canonical document object keys:

- `documents/{tenant_id}/{document_id}/original`
- `documents/{tenant_id}/{document_id}/ocr/raw_text.json`
- `documents/{tenant_id}/{document_id}/artifacts/...`

## `docuparse_storage` — selecting a backend (feature 011)

Application code MUST use `get_storage()` as the single instantiation point
instead of building a backend directly:

```python
from docuparse_storage import get_storage
storage = get_storage()            # workers/services (reads env)
storage = get_storage(local_dir=settings.DOCUPARSE_LOCAL_STORAGE_DIR)  # preserva o default local do serviço
```

`get_storage()` returns a `RoutingStorage` that **writes** to the configured
backend and **reads** by dispatching on the URI scheme (`local://` vs `s3://`),
so legacy references stay readable during an incremental migration.

Environment variables (credentials/endpoint always from env/secret):

| Var | Default | Notes |
|---|---|---|
| `DOCUPARSE_STORAGE_BACKEND` | `local` | `local` (comportamento atual) ou `s3` |
| `DOCUPARSE_LOCAL_STORAGE_DIR` | por serviço | usado no modo local e para ler `local://` legado |
| `S3_ENDPOINT_URL` | — | endpoint MinIO (vazio ⇒ AWS S3) |
| `S3_BUCKET` / `S3_REGION` | — | obrigatórios quando `s3` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | — | via k8s Secret |

`boto3` is imported lazily (only when the effective backend is `s3`). Migration
of existing data: `scripts/migrate_storage_local_to_s3.py --dry-run|--apply`.
