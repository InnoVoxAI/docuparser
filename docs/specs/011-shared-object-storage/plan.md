# Implementation Plan: Armazenamento de objetos compartilhado entre backends

**Branch**: `011-shared-object-storage` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `docs/specs/011-shared-object-storage/spec.md`
**Fonte de apoio**: [docs/fixplans/storage-s3-minio-migration-plan.md](../../fixplans/storage-s3-minio-migration-plan.md) (análise de código já validada contra o repositório real)

## Summary

Substituir o armazenamento local não compartilhado (cada serviço grava no disco do próprio pod) por um storage de objetos compatível com S3/MinIO, compartilhado entre todos os backends, **sem regressão** do comportamento atual. A abstração de storage já existe (`shared/docuparse_storage`, hoje só com `LocalStorage`) e a maior parte da I/O já passa por ela; o `README` do pacote já declara MinIO/S3 como o backend do ambiente integrado. A abordagem: introduzir uma implementação `S3Storage` com o **mesmo contrato** de `LocalStorage`, um `RoutingStorage` que despacha leituras pelo esquema da URI (`local://` vs `s3://`) e escreve no backend configurado por ambiente, e uma fábrica `get_storage()` como único ponto de instanciação. Backend selecionável por env com **default `local`** (comportamento idêntico ao atual), coexistência de URIs legadas para migração incremental e rollback, e falhas de storage sempre explícitas (nunca documento sem arquivo).

## Technical Context

**Language/Version**: Python 3.13 (backend-com, backend-ocr, workers); Python 3.13 assumido para layout/langextract; backend-core em Django 5.0.1 (Python 3.10+ no venv atual)

**Primary Dependencies**: backend-core = Django 5.0.1 + DRF 3.14; backend-com/ocr/layout/langextract = FastAPI + pydantic; pacote compartilhado `docuparse_storage`; **nova dependência: `boto3`** (importada de forma lazy, só quando `DOCUPARSE_STORAGE_BACKEND=s3`)

**Storage**: objetos binários (arquivo original + `raw_text.json`) — hoje `LocalStorage` em disco por pod; alvo = MinIO/S3-compatível. Metadados/referências em PostgreSQL (`Document.file_uri`, `Document.raw_text_uri`, `CharField(1024)`) e em eventos (`DocumentReceivedEvent.data.file.uri`, `OCRCompletedEvent.data.raw_text_uri`)

**Testing**: pytest. Unit com `moto` (mock S3, sem rede/disco — exigência da constituição); integração com MinIO real para o contrato cross-serviço

**Target Platform**: Linux (containers Docker) em Kubernetes (staging/produção); múltiplos serviços em pods separados

**Project Type**: web-service multi-serviço (monorepo `docuparse-project/` com pacote compartilhado)

**Performance Goals**: servir/gravar documentos de até 20 MB sem estouro de memória (limite de container 2 GB) nem timeout; endpoints não-processadores do core dentro de 200 ms p95 (constituição) — a leitura do arquivo não deve regredir esse orçamento

**Constraints**: sem downtime na migração; sem regressão no modo default; credenciais apenas via env/secret; leitura consistente pós-escrita entre serviços

**Scale/Scope**: 5 serviços com I/O de artefatos + 1 pacote compartilhado; ~13 pontos de leitura/escrita já mapeados, 2 órfãos que burlam a abstração

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Situação |
|---|---|---|
| **I. Code Quality** | `S3Storage`/`RoutingStorage` com type hints, funções single-purpose ≤50 linhas, arquivos ≤400 linhas; credenciais fora do código (env/secret); validação de key mantida (`_validate_key`) evitando path traversal | ✅ PASS |
| **II. Testing Standards** | Unit tests **não** tocam rede/disco → `moto` para S3; contrato inter-serviço (core↔ocr↔layout↔langextract) coberto por integração com MinIO; parametrizar os testes de storage existentes p/ os dois backends; regressão: teste que reproduz "documento servido de pod distinto" | ✅ PASS |
| **III. UX Consistency** | Endpoint `/documents/{id}/file` mantém envelope/headers e `content_type` idênticos (FR-009); mensagens de erro de storage humanas e sem stack trace; distinção "não encontrado" vs "indisponível" (FR-006/FR-007) | ✅ PASS |
| **IV. Performance** | Fase 1 mantém `FileResponse(BytesIO)` (paridade); 20 MB dentro do limite de 2 GB/container; streaming/presigned como otimização posterior; boto3 com timeout/retry configurados | ✅ PASS |
| **Technology Standards** | MinIO/S3 já é o backend declarado no `shared/README.md` para o ambiente integrado — **não** é adição de engine/AI que exija emenda. `boto3` é dependência de infraestrutura consistente com o padrão declarado | ✅ PASS (sem emenda) |
| **Development Workflow** | Spec-first (esta feature) já cumprida; branch `011-...`; PR com plano de testes referenciando esta spec | ✅ PASS |

**Resultado**: sem violações. Nenhuma entrada em Complexity Tracking necessária.

## Project Structure

### Documentation (this feature)

```text
docs/specs/011-shared-object-storage/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Phase 0 — decisões e resolução das clarificações
├── data-model.md        # Phase 1 — entidades e formato de referência
├── quickstart.md        # Phase 1 — como configurar, testar e migrar
├── contracts/           # Phase 1 — contrato da interface Storage, URIs e env
│   ├── storage-interface.md
│   ├── storage-uri.md
│   └── storage-config.md
├── checklists/
│   └── requirements.md  # (criado no /speckit-specify)
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
docuparse-project/
├── shared/
│   └── docuparse_storage/          # ALVO PRINCIPAL da mudança
│       ├── __init__.py             # reexporta símbolos (compat de imports)
│       ├── keys.py                 # StoredObject + document_*_key (extraído)
│       ├── base.py                 # Protocol Storage
│       ├── local.py                # LocalStorage (extraído do __init__ atual)
│       ├── s3.py                   # S3Storage (novo; adapta scripts/s3/s3.py)
│       ├── routing.py              # RoutingStorage (novo)
│       └── factory.py              # get_storage() (novo)
│   └── tests/
│       └── test_storage_and_events.py   # parametrizar local + s3(moto)
├── backend-com/
│   └── src/backend_com/
│       ├── config.py               # envs de storage
│       └── services/document_ingest.py   # get_storage() (escrita do original)
├── backend-core/
│   ├── core/settings.py            # envs de storage
│   └── documents/
│       ├── views.py                # get_storage() (serve /file; lê raw_text)
│       ├── serializers.py          # get_storage() (lê raw_text)
│       └── services/ocr_processor.py     # get_storage() (lê/escreve)
├── backend-ocr/application/ocr_event_worker.py       # wiring get_storage()
├── layout-service/
│   ├── application/layout_event_worker.py            # wiring get_storage()
│   └── api/app.py                  # ÓRFÃO 1: remover path cru → get_storage()
├── langextract-service/application/extraction_event_worker.py  # wiring
└── scripts/
    └── migrate_storage_local_to_s3.py   # migração idempotente (novo)
```

**Structure Decision**: monorepo multi-serviço já existente. O núcleo da mudança fica **concentrado no pacote compartilhado** `shared/docuparse_storage/`; os serviços mudam apenas o **ponto de instanciação** (`LocalStorage(...)` → `get_storage()`) e a config de env. Isso mantém a lógica de leitura/escrita e os handlers dos workers intactos, favorecendo baixo risco e reversibilidade.

## Complexity Tracking

> Sem violações de constituição. Seção não aplicável.
