# Quickstart — Storage compartilhado (S3/MinIO)

Feature: `011-shared-object-storage`. Guia de configuração, teste e migração.

## 1. Modo local (default — comportamento atual)

Nada a fazer. Sem `DOCUPARSE_STORAGE_BACKEND`, todos os serviços usam `LocalStorage` como hoje. Referências ficam `local://…`.

## 2. Ativar storage compartilhado (staging/produção)

Definir nas envs de **todos** os serviços de I/O (com, core, ocr, layout, langextract), via k8s Secret:

```bash
DOCUPARSE_STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://minio.<namespace>.svc:9000   # vazio p/ AWS S3
S3_BUCKET=docuparse
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=<secret>
AWS_SECRET_ACCESS_KEY=<secret>
```

Pré-requisito de infra: bucket `docuparse` provisionado (a app não cria bucket em runtime).

## 3. Rodar localmente contra MinIO (dev/integração)

```bash
docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"
# criar bucket "docuparse" via console/mc, então exportar as envs acima com
# S3_ENDPOINT_URL=http://localhost:9000
```

## 4. Testes

- **Unit** (sem rede/disco — constituição): `S3Storage` contra `moto`. Parametrizar `shared/tests/test_storage_and_events.py` para `local` e `s3(moto)` — mesmo `StoredObject`, mesmo roundtrip, `NoSuchKey → FileNotFoundError`.
- **RoutingStorage**: dispatch por esquema (`local://`, `s3://`, key nua).
- **Integração** (MinIO real): pipeline cross-serviço (com → core → ocr → layout → langextract) lendo artefatos entre "pods"; servir `/documents/{id}/file`; documento de 20 MB; falha de conexão/credencial → erro explícito; referência legada `local://` abre com `s3` ligado.

Mapeamento para critérios de aceite: SC-001/SC-003 (cross-serviço), SC-002 (serve /file de outro pod), SC-004 (20 MB), SC-005 (falha explícita), SC-006 (legado), SC-007 (paridade no default).

## 5. Migração dos dados existentes (sem downtime)

```bash
python docuparse-project/scripts/migrate_storage_local_to_s3.py --dry-run
python docuparse-project/scripts/migrate_storage_local_to_s3.py --apply
```

Comportamento: idempotente e retomável. Para cada `Document` com `file_uri`/`raw_text_uri` em `local://…`: lê os bytes do disco, faz `put` no S3, atualiza a URI no DB para `s3://…`. Como o `RoutingStorage` resolve por esquema, itens ainda não migrados continuam legíveis durante todo o processo.

## 6. Rollback

Voltar `DOCUPARSE_STORAGE_BACKEND=local`. Nenhuma migração de schema foi feita (URIs são `CharField`). Manter as credenciais S3 configuradas para continuar lendo o que já foi para `s3://`.

## 7. Perguntas de deploy pendentes (não bloqueiam o código)

- Existe PVC ReadWriteMany já montado igual em todos os pods? (muda a extensão do problema, não o design)
- Valores concretos de endpoint/bucket/região e origem dos segredos (k8s Secret vs Vault)?
- Política de retenção/lifecycle do bucket (gerida por infra)?

## 8. Fora de escopo (lembretes)

- **Bug de rede com→core** ("documento não aparece na listagem") — problema distinto; esta feature não o resolve.
- **`approved_exporter` (export ERP)** — permanece em volume dedicado; migrar só se confirmado consumo cross-backend.
