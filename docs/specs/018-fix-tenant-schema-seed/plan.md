# Implementation Plan: Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants

**Branch**: `018-fix-tenant-schema-seed` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `docs/specs/018-fix-tenant-schema-seed/spec.md`

## Summary

Mover `SchemaConfig` e `LayoutConfig` do app tenant-scoped `documents` para um novo app
**`catalog` em `SHARED_APPS`**, materializando-os como tabelas únicas no schema `public`.
Todo tenant passa a ler o mesmo catálogo via `search_path` do django-tenants (sem cópia por
schema, sem passo de provisionamento). Escrita (criar/editar/desativar/remover) fica restrita
a operador de plataforma (`tenants.manage`); leitura permanece aberta a qualquer usuário
autenticado do tenant e ao token de serviço interno (pipeline de extração).

A transição consolida as N cópias por-schema numa cópia global a partir da fonte canônica
(`backend-core/models/*/definition.py`), com uma verificação de divergência que **aborta** a
migração destrutiva se algum tenant tiver linhas fora do conjunto canônico (FR-010).
Código morto removido: `documents/startup.py::ensure_default_schemas` + o `try/except`
que o engolia em `documents/apps.py`, e o laço de seed por-tenant em `seed_data.py`.

## Technical Context

**Language/Version**: Python 3.11+ (backend-core roda em 3.13 no devcontainer), Django (latest stable) + django-tenants; TypeScript/React + Vite no frontend.

**Primary Dependencies**: `django-tenants` (roteamento de schema, `migrate_schemas`, `schema_context`), Django REST Framework, `rest_framework_simplejwt`. Frontend: `@tanstack/react-query`.

**Storage**: PostgreSQL, multi-tenant schema-per-tenant. `public` = SHARED_APPS (`django_tenants`, `auth`, `users`, `tenants`, …); `tenant_<slug>` = TENANT_APPS (`documents`, `orchestrator`). Este plano move o catálogo de tipos de documento de TENANT_APPS → SHARED_APPS.

**Testing**: `pytest` + `pytest-django` no backend-core (rodar via `/docuparser/run_script.sh <cmd>` para injetar env e alcançar o Postgres do devcontainer). Vitest no frontend.

**Target Platform**: Linux server (Docker Compose). Migrações aplicadas por `backend-core/entrypoint.sh` (`migrate_schemas --shared` → `migrate_schemas` → `seed_data`).

**Project Type**: Web (Django API `backend-core` + React `frontend`), num monorepo com serviços auxiliares (backend-ocr, langextract-service, layout-service) fora do escopo.

**Performance Goals**: Sem mudança de perfil. O catálogo é lido no hot path de extração (`_resolve_schema_for_extraction`) — hoje 1–3 queries por documento; continua igual (mesma query, tabela em `public`). Endpoints não-processamento < 200 ms p95 (constituição §IV).

**Constraints**:
- Isolamento entre tenants preservado para tudo que não seja o catálogo (documentos, extração, validação, OCR/integration/email settings continuam por schema).
- A migração destrutiva (`DeleteModel` das tabelas por-tenant) NÃO pode rodar antes da verificação de divergência (FR-010) nem antes do seed global (FR-007).
- Identificadores de schema/layout preservados (FR-015): documentos já processados referenciam por `CharField`, não FK.
- Guardrail do CLAUDE.md: migração que já pode ter rodado em produção → runbook explícito + verificação read-only antes do passo destrutivo.

**Scale/Scope**: Poucos tenants (ambiente atual conhecido e limitado). 2 `SchemaConfig` canônicos (`nota_fiscal_default`, `conta_agua_default`) + 3 `LayoutConfig` (`nota_fiscal`, `fatura_condominio`, `fatura_energia`). ~1 novo app Django, ~4 migrações, ~1 management command, ~6 arquivos de código tocados no backend, ~3 no frontend, docs normativas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| **I. Code Quality** — sem dead code | A feature **remove** dead code (`ensure_default_schemas`, seed loop, `try/except` mudo). Novo app `catalog` pequeno, com type hints. Funções < 50 linhas, arquivos < 400. | ✅ Reforça |
| **I. Code Quality** — segurança / boundaries | Escrita no catálogo passa a exigir permissão de plataforma (`tenants.manage`) — hoje qualquer `tenantAdmin` com `models.edit` podia editar; a mudança **restringe** o boundary. Sem SQL dinâmico: a leitura cross-schema na verificação de divergência usa o ORM dentro de `schema_context`, não string SQL. | ✅ Reforça |
| **II. Testing Standards** — regressão | Bug conhecido ("tenant novo sem catálogo") ganha teste de regressão: provisionar tenant → catálogo visível sem seed. Testes de contrato para os endpoints do catálogo (permissão + globalidade). Migração de consolidação com teste (idempotência + abort em divergência). | ✅ (tarefas no /speckit-tasks) |
| **II. Testing Standards** — isolamento | Testes unit não fazem rede/disco. Testes de multi-tenant já usam Postgres real (marca de integração). | ✅ |
| **III. UX Consistency** — envelope, terminologia | Endpoints do catálogo mantêm o formato de resposta atual (lista simples hoje; não regride). Terminologia "layout"/"schema"/"tipo de documento" mantida. Frontend: UI de gestão do catálogo só habilitada para operador de plataforma, com aviso "afeta todos os tenants". | ✅ |
| **IV. Performance** | Nenhuma query nova no hot path; mesma cardinalidade. `migrate_schemas` custa 1 CreateModel em `public` + 1 DeleteModel por schema de tenant (poucos). | ✅ |
| **Technology Standards** | Django + PostgreSQL + django-tenants (já no stack). Nenhuma dependência nova. | ✅ |
| **Development Workflow** | Spec-first (feito). Branch `018-fix-tenant-schema-seed` (convenção `feat/###` não seguida à risca no repo — branches existentes usam `NNN-slug`; manter consistência com o repo). Conventional Commits. | ✅ |

**Resultado**: PASS. Nenhuma violação — a feature melhora a aderência aos princípios I e II. Sem entradas em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
docs/specs/018-fix-tenant-schema-seed/
├── plan.md              # Este arquivo
├── spec.md              # Especificação (replanejada 2026-09-07)
├── research.md          # Fase 0 — decisões técnicas
├── data-model.md        # Fase 1 — modelos e migrações
├── quickstart.md        # Fase 1 — runbook de deploy/transição + validação
├── contracts/
│   └── catalog-endpoints.md   # Contrato REST do catálogo global
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
docuparse-project/backend-core/
├── catalog/                         # NOVO app — SHARED_APPS
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                    # SchemaConfig, LayoutConfig (movidos de documents)
│   ├── defaults.py                  # fonte de verdade: canonical specs a partir de models/*/definition.py
│   ├── serializers.py               # SchemaConfigSerializer, LayoutConfigSerializer (movidos)
│   ├── views.py                     # endpoints do catálogo (movidos de documents/views.py), perm = tenants.manage p/ escrita
│   ├── urls.py
│   ├── management/commands/
│   │   └── check_catalog_divergence.py   # read-only: aborta se algum tenant tem linhas fora do canônico
│   ├── migrations/
│   │   ├── 0001_initial.py          # CreateModel em public
│   │   └── 0002_seed_default_catalog.py  # data migration idempotente (populate a partir de defaults.py)
│   └── tests/
│       ├── test_models.py
│       ├── test_catalog_api.py      # permissão + globalidade
│       └── test_consolidation.py    # idempotência + abort em divergência
├── documents/
│   ├── models.py                    # REMOVE SchemaConfig, LayoutConfig
│   ├── serializers.py               # re-export/import de catalog p/ compat, ou ajustar imports
│   ├── views.py                     # remove os 4 views do catálogo (movidos p/ catalog)
│   ├── urls.py                      # remove as rotas (agora em catalog.urls)
│   ├── apps.py                      # REMOVE o try/except ensure_default_schemas
│   ├── startup.py                   # REMOVE ensure_default_schemas
│   ├── services/ocr_processor.py    # troca import: from catalog.models import ...
│   └── migrations/
│       └── 0012_drop_catalog_models.py  # RunPython(verify canonical-only) + DeleteModel x2 (roda por schema de tenant)
├── users/management/commands/seed_data.py   # REMOVE bloco DEFAULT_SCHEMAS/DEFAULT_LAYOUT_CONFIGS; chama catalog.defaults.seed() no public
├── core/
│   ├── settings.py                  # adiciona "catalog" em SHARED_APPS
│   └── urls.py                      # inclui catalog.urls sob /api/ocr/ (rota tenant, leitura em contexto de tenant)
└── models/{nota_fiscal,contadeagua}/definition.py   # inalterado — fonte canônica consumida por catalog/defaults.py

docuparse-project/frontend/src/
├── modules/settings/hooks/
│   ├── useLayoutMutations.ts        # remove tenant_slug do input; sem mudança de endpoint
│   └── useSchemaMutations.ts        # idem
├── modules/settings/components/
│   ├── SchemaList.tsx / ConfigList.tsx / SettingsView.tsx  # gate de escrita por permissão de plataforma + aviso "afeta todos os tenants"
└── shared/lib/permissions (ou equivalente)   # helper isPlatformOperator, se não existir

docs/specs/010-multi-tenancy-schemas/data-model.md   # nota de superseded (FR-016)
```

**Structure Decision**: App Django novo `catalog` no `backend-core`, registrado em `SHARED_APPS`
(antes dos TENANT_APPS). É o mecanismo suportado pelo django-tenants para uma tabela viver no
schema `public` e ser lida transparentemente de qualquer schema de tenant. `documents`
permanece TENANT_APP. Frontend continua no módulo `settings` existente — nenhuma rota nova,
apenas gating de permissão e cópia.

## Complexity Tracking

> Sem violações de constituição. Nada a justificar.
