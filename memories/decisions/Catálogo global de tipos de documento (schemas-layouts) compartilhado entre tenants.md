---
title: Catálogo global de tipos de documento (schemas/layouts) compartilhado entre
  tenants
type: note
permalink: docuparser/decisions/catalogo-global-de-tipos-de-documento-schemas-layouts-compartilhado-entre-tenants
tags:
- 018-fix-tenant-schema-seed
- multi-tenancy
- layouts
- schema-config
- architecture
---

## Decisão

O spec `018-fix-tenant-schema-seed` foi **replanejado em 2026-09-07**. Deixou de ser
"provisionar SchemaConfig/LayoutConfig padrão dentro de cada tenant" e passou a ser:

**Os tipos de documento (SchemaConfig + LayoutConfig) tornam-se um catálogo GLOBAL,
compartilhado, vivendo no schema `public` — não pertencem a nenhum tenant.**

## Por quê

- Elimina a causa raiz do [[Bug conhecido: tenants criados via convite não recebem SchemaConfig/LayoutConfig padrão]] em vez de remediá-la: se o catálogo é global, "tenant novo sem tipos de documento" deixa de ser um estado possível.
- Fonte de verdade única (exigência desde o pedido original).
- `SchemaConfig`/`LayoutConfig` já não têm FK `tenant` (removida na migration `documents/0011_remove_tenant_fk`); o único FK é `LayoutConfig → SchemaConfig` (interno, migra junto). `Document.layout` e `ExtractionResult.schema_id` são `CharField`, não FK → nenhum FK cross-schema quebra ao mover.
- `django-tenants` mantém `public` no `search_path` em contexto de tenant, então um app em `SHARED_APPS` é lido/escrito normalmente de dentro de qualquer tenant (é como `users`/`tenants` funcionam).

## Decisões de arquitetura fixadas com o solicitante

1. **100% global**, sem override por tenant. Sem mecanismo de layout exclusivo de tenant.
2. **Só operador de plataforma** (permissão `tenants.manage`) cria/edita/ativa/remove no catálogo. Tenants têm acesso **somente-leitura**. Hoje os endpoints usam `require_permission("models.edit")` em contexto de tenant — precisa mudar para permissão de plataforma.
3. Assume-se **sem customização real** em produção além dos 3 padrão (nota fiscal, fatura de água/condomínio, fatura de energia). A transição é uma **migração única de consolidação** que popula o catálogo global a partir da fonte canônica (`contracts`/`shared` `models/*/definition.py`) e dropa as tabelas per-schema. Se encontrar divergência/conflito de identificador → **para e sinaliza**, não descarta.

## Impacto / escopo

- Reverte **parcialmente** `010-multi-tenancy-schemas` US4 — só para o catálogo de tipos de documento. OCR settings, integration settings, email settings **continuam por tenant**.
- Remover código morto: `documents/startup.py::ensure_default_schemas` e o laço de seed por-tenant em `users/management/commands/seed_data.py` (~linhas 167-219).
- `_provision_tenant` (`tenants/views.py`) não ganha nenhuma etapa de tipos de documento.
- Provável novo app em `SHARED_APPS` (ex. `catalog`) contendo os dois modelos.
- Atualizar doc normativa: `datamodel_reference.md` e a nota da decisão 010 US4.
- Frontend: `modules/settings` (hooks de layout/schema) — gestão vira operação de plataforma.

## Status

**IMPLEMENTADO** — branch `018-fix-tenant-schema-seed`, 2026-09-07 (`/speckit-implement`).
Ainda não commitado / mergeado.

Entregue conforme o plano (`docs/specs/018-fix-tenant-schema-seed/`):

- **App `catalog`** (`docuparse-project/backend-core/catalog/`) em `SHARED_APPS` após `users`:
  `models.py` (SchemaConfig/LayoutConfig + `TimeStampedModel` local, constraints canônicas
  `unique_schema_config_version` / `unique_layout_config`), `defaults.py`
  (`default_catalog_specs()`, `PROTECTED_SCHEMA_IDS`, `seed_default_catalog()` idempotente),
  `serializers.py`, `permissions.py` (`CatalogPermission`: leitura = `models.edit` OU
  `tenants.manage`, escrita = `tenants.manage`, token de serviço sempre liberado),
  `views.py` + `urls.py` (mesmas rotas `/api/ocr/schema-configs`, `.../<uuid>`,
  `/api/ocr/layout-configs`), `management/commands/check_catalog_divergence.py`.
- **Migrações**: `catalog/0001_initial`, `catalog/0002_seed_default_catalog` (RunPython);
  `documents/0014_drop_legacy_catalog_constraints` (não-destrutivo, resolve colisão de nome
  de constraint durante a coexistência); `documents/0015_drop_catalog_models`
  (`assert_only_canonical_rows` como guarda de divergência → `RuntimeError` nomeando o
  schema, seguido de `DeleteModel` x2). **`0015` ainda NÃO foi aplicado em produção** — ver
  runbook em `quickstart.md` (backup + `check_catalog_divergence` pré-deploy).
- **Imports reapontados** para `catalog.models`: `ocr_processor.py`, `documents/views.py`
  (`document_langextract_view`), testes.
- **Código morto removido**: `documents/startup.py::ensure_default_schemas`, o `try/except`
  mudo em `documents/apps.py::ready()`, o laço de seed por-tenant em `seed_data.py`
  (substituído por uma chamada única `seed_default_catalog()` no schema público).
- **Frontend** (`modules/settings`): `tenant_slug` removido de `useSchemaMutations` /
  `useLayoutMutations` (+ callers); `ExtractionPanel` divide em `ExtractionBuilder`
  (só `tenants.manage`) vs. visão somente-leitura; novo `CatalogScopeNotice`
  ("afeta todos os tenants" / "somente leitura"); `SchemaList` ganhou prop `readOnly`.
- **Docs**: nota "Superseded by 018" em `docs/specs/010-multi-tenancy-schemas/data-model.md`;
  `CLAUDE.md` SPECKIT → `018.../plan.md`.

Testes: `pytest catalog documents orchestrator users tenants` → 223 passed, 1 skipped.
Frontend `vitest` módulo `settings` → verde; typecheck/lint limpos. (`flows.test.tsx` e
`pagination.test.tsx` falham no HEAD limpo — pré-existentes, não relacionados.)

Limitação conhecida: os testes `tenant_db` de classe pytest simples
(`CatalogGlobalityTests`, regressão cross-tenant) não são coletados pelo
`python_classes = Test*` do `pytest.ini` — mesmo problema pré-existente de
`tenants/tests/test_isolation.py::TenantIsolationTests`. Cobertura equivalente vive em
`CatalogPermissionMatrixTests` (`TestCase`, coletado).

## Relations

- relates_to [[Multi-Tenancy — PostgreSQL Schema-per-Tenant]]
- supersedes_partially [[010-multi-tenancy-schemas]] US4 (tenant-scoped schema/layout configs)
- resolves [[Bug conhecido: tenants criados via convite não recebem SchemaConfig/LayoutConfig padrão]]
- relates_to [[models.edit permission enforced on schema/layout/settings endpoints]]
