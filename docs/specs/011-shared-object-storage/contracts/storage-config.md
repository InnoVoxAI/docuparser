# Contrato — Configuração de storage por ambiente

Todas as configurações vêm de variáveis de ambiente (origem: k8s Secret / env). **Nenhum valor sensível no código** (FR-008).

## Variáveis

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `DOCUPARSE_STORAGE_BACKEND` | não | `local` | `local` (comportamento atual) ou `s3` |
| `DOCUPARSE_LOCAL_STORAGE_DIR` | não | (atual por serviço) | Raiz do disco local; usado no modo `local` e p/ ler `local://` legado |
| `S3_ENDPOINT_URL` | só se `s3` | — | Endpoint MinIO/S3 (vazio ⇒ AWS S3 nativo) |
| `S3_BUCKET` | só se `s3` | — | Bucket dos artefatos |
| `S3_REGION` | só se `s3` | — | Região |
| `AWS_ACCESS_KEY_ID` | só se `s3` | — | Credencial (via Secret) |
| `AWS_SECRET_ACCESS_KEY` | só se `s3` | — | Credencial (via Secret) |

## Regras

1. **Default preserva o atual**: sem `DOCUPARSE_STORAGE_BACKEND`, o sistema opera exatamente como hoje (SC-007).
2. **Ativação explícita**: `DOCUPARSE_STORAGE_BACKEND=s3` liga o storage compartilhado em todos os serviços que compartilham a config.
3. **Import lazy**: `boto3` só é importado quando o backend efetivo é `s3` — serviços em `local` não exigem a dependência em runtime.
4. **Falha de config**: backend `s3` sem `S3_BUCKET`/credenciais **MUST** falhar de forma explícita na inicialização/primeiro acesso — nunca cair silenciosamente em local.
5. **Bucket provisionado por infra**: a aplicação **não** cria bucket em runtime (`ensure_bucket` não é chamado no caminho de produção).
6. **Rollback**: voltar `DOCUPARSE_STORAGE_BACKEND=local` restaura o comportamento anterior; manter credenciais S3 configuradas permite continuar lendo `s3://` já migrados.

## Consistência entre serviços

Os serviços que trocam artefatos (com, core, ocr, layout, langextract) **MUST** compartilhar o mesmo backend/bucket para que a leitura cross-serviço funcione (SC-001/SC-003).
