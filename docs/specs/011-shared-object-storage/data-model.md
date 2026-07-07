# Phase 1 — Data Model

Feature: Armazenamento de objetos compartilhado entre backends (`011-shared-object-storage`)

Esta feature **não altera o schema do banco**. Ela introduz/estende tipos na camada de storage e formaliza o formato da referência de artefato. Abaixo, as entidades conceituais e as regras.

---

## Entidade: Artefato (Artifact)

Unidade de conteúdo binário persistida e compartilhada entre serviços.

| Campo | Tipo | Descrição |
|---|---|---|
| `content` | bytes | Conteúdo binário do artefato |
| `key` | str | Chave lógica estilo S3, estável entre backends |
| `uri` | str | Referência persistível com esquema (`local://<key>` ou `s3://<bucket>/<key>`) |
| `size_bytes` | int | Tamanho do conteúdo |
| `sha256` | str | Hash do conteúdo (integridade) |

**Tipos em escopo** (apenas estes dois):
- **Arquivo original** — key: `documents/{tenant_id}/{document_id}/original`
- **`raw_text.json`** — key: `documents/{tenant_id}/{document_id}/ocr/raw_text.json`

**Representação em código**: `StoredObject` (dataclass já existente em `docuparse_storage`), retornado por `put_bytes`. **Contrato preservado**: `uri`, `key`, `size_bytes`, `sha256`.

**Regras de validação** (mantidas de `LocalStorage._validate_key`, aplicáveis a todos os backends):
- key não pode ser absoluta, conter `..`, nem ser vazia (proteção contra path traversal).

---

## Entidade: Referência de Artefato (Artifact Reference)

Ponteiro persistido que localiza um artefato. É o que trafega no banco e nos eventos.

| Local de persistência | Campo | Tipo atual | Observação |
|---|---|---|---|
| DB (`Document`) | `file_uri` | `CharField(max_length=1024)` | Arquivo original |
| DB (`Document`) | `raw_text_uri` | `CharField(max_length=1024, blank=True)` | `raw_text.json` |
| Evento `DocumentReceivedEvent` | `data.file.uri` | str | Propagado com→core→ocr |
| Evento `OCRCompletedEvent` | `data.raw_text_uri` | str | Propagado ocr→layout→extração |

**Formatos válidos (coexistentes)**:
- **Legado**: `local://documents/{tenant}/{document}/...`
- **Novo**: `s3://{bucket}/documents/{tenant}/{document}/...`

**Regra de resolução** (RoutingStorage): o esquema da URI determina o backend de leitura. URIs legadas continuam resolvendo mesmo com o backend de escrita = `s3` (FR-004, coexistência).

**Máscara de tamanho**: `s3://{bucket}/{key}` cabe folgado em `CharField(1024)` — **sem migração de schema**.

**Transições de estado da referência** (durante migração — FR-005):
```
local://…  --(migração idempotente: copia bytes p/ S3, atualiza DB)-->  s3://…
```
Enquanto não migrada, permanece `local://…` e continua legível. A migração é retomável e não bloqueante (sem downtime).

---

## Entidade: Backend de Storage (Storage Backend)

Origem/destino físico dos artefatos, selecionável por ambiente.

| Modo | Ativação | Escrita | Leitura |
|---|---|---|---|
| `local` (default) | `DOCUPARSE_STORAGE_BACKEND` ausente ou `local` | disco local (`DOCUPARSE_LOCAL_STORAGE_DIR`) | por esquema (`local://` local; `s3://` S3 se configurado) |
| `s3` | `DOCUPARSE_STORAGE_BACKEND=s3` | MinIO/S3 (`S3_BUCKET`) | por esquema (`local://` legado; `s3://` S3) |

**Invariantes**:
- No modo default, o comportamento observável é idêntico ao atual (SC-007).
- Toda falha de acesso é explícita; nenhum `Document` é persistido sem o artefato correspondente (FR-006).
- `NoSuchKey`/404 é distinguível de indisponibilidade/credencial (FR-007).
