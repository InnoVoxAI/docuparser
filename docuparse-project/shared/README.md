# Shared development adapters

Initial foundation decisions:

- Event bus: Redis Streams for the integrated environment. The local `LocalJsonlEventBus` adapter is intentionally tiny and is used only for deterministic contract and smoke tests.
- Storage: MinIO/S3-compatible object storage for the integrated environment. The local `LocalStorage` adapter preserves the same object-key convention for unit tests and local scripts.

Canonical document object keys:

- `documents/{tenant_id}/{document_id}/original`
- `documents/{tenant_id}/{document_id}/ocr/raw_text.json`
- `documents/{tenant_id}/{document_id}/artifacts/...`
