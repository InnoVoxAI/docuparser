# Contrato — Formato de URI de artefato

Referências persistidas no banco e propagadas em eventos. A coexistência de esquemas é o que habilita migração incremental e rollback (FR-004).

## Esquemas

| Esquema | Formato | Quando |
|---|---|---|
| `local://` | `local://<key>` | Backend local (default) e todas as referências legadas |
| `s3://` | `s3://<bucket>/<key>` | Backend S3/MinIO |

Onde `<key>` é uma das chaves canônicas:
- `documents/{tenant_id}/{document_id}/original`
- `documents/{tenant_id}/{document_id}/ocr/raw_text.json`

## Regras

1. **Resolução por esquema**: o leitor (`RoutingStorage.get_bytes`) escolhe o backend a partir do prefixo da URI, independentemente do backend de **escrita** configurado.
2. **Estabilidade da key**: a `key` é idêntica entre backends; só o prefixo/esquema muda. Isso permite copiar `local://k` → `s3://bucket/k` mantendo `k`.
3. **Compatibilidade de armazenamento**: `s3://{bucket}/{key}` cabe em `CharField(max_length=1024)` — sem migração de schema.
4. **Key nua**: quando um consumidor passa uma key sem esquema, resolve-se no backend default configurado.
5. **Validação**: keys com caminho absoluto, `..` ou vazias são rejeitadas em qualquer backend.

## Exemplos

```
local://documents/tenant-demo/6f0e.../original
s3://docuparse/documents/tenant-demo/6f0e.../original
local://documents/tenant-demo/6f0e.../ocr/raw_text.json
s3://docuparse/documents/tenant-demo/6f0e.../ocr/raw_text.json
```

## Invariante de migração

Uma referência migra `local://…` → `s3://…` **apenas após** os bytes existirem no destino. Antes disso, a referência legada permanece válida e legível (sem downtime).
