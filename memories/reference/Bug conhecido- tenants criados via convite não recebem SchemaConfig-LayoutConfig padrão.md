---
title: 'Bug conhecido: tenants criados via convite não recebem SchemaConfig/LayoutConfig
  padrão'
type: note
permalink: docuparser/reference/bug-conhecido-tenants-criados-via-convite-nao-recebem-schema-config-layout-config-padrao
tags:
- bug
- tenants
- seed-data
- 017-tenant-admin-onboarding
---

## Contexto

Durante a fase 6 (Polish) de [[017-tenant-admin-onboarding]], decidimos que `seed_data.py`
(`docuparse-project/backend-core/users/management/commands/seed_data.py`) deve ter um
guardrail: rodar apenas quando o banco estiver vazio (`Tenant.objects.exists() is False`).
Se já existir qualquer `Tenant`, o comando inteiro vira no-op.

Motivação: o loop antigo `for t in Tenant.objects.filter(is_active=True)` criava um admin
fake (`admin@{slug}`) com senha compartilhada para *qualquer* tenant sem admin próprio —
inclusive tenants criados pelo fluxo real de convite (US1), gerando um usuário fantasma ao
lado do admin real. Com o guardrail, o único tenant que o seed jamais cria é o tenant
default (InnoVox); todo outro tenant nasce só via `_provision_tenant` / `create_admin_invite`.

## O bug

`seed_data.py` também popula `SchemaConfig`/`LayoutConfig` padrão (nota fiscal, fatura de
água/condomínio, fatura de energia) via `schema_context(t.schema_name)`, iterando sobre
todos os tenants ativos. Com o guardrail acima, essa seção só roda no primeiro seed —
ou seja, **só o tenant default recebe esses schemas/layouts**.

Tenants criados depois via fluxo de convite real (`_provision_tenant` em
`tenants/views.py`) **não** recebem `SchemaConfig`/`LayoutConfig` nenhum. Isso é um bug
pré-existente (não introduzido por esta feature, só exposto por ela), fora do escopo de
017-tenant-admin-onboarding.

Existe também `documents/startup.py::ensure_default_schemas()`, que parece uma tentativa
de resolver algo parecido, mas:
- só cobre o tenant cujo `name == "default"` (não todos os tenants);
- usa um campo `tenant` FK em `SchemaConfig` que parece divergir do modelo usado em
  `seed_data.py` (que usa `schema_context` por schema Postgres, sem FK `tenant`).
Não está claro se esse código é usado de fato ou é legado morto — precisa investigação
antes de virar a correção definitiva.

## Correção sugerida (não implementada)

`_provision_tenant` (ou um signal `post_save` em `Tenant`) deveria, ao criar um novo
tenant, copiar/seedar os `SchemaConfig`/`LayoutConfig` padrão para o schema Postgres do
tenant novo — o mesmo bloco de código que hoje vive em `seed_data.py` linhas ~172-223,
extraído para uma função reutilizável (ex. `tenants/services.py::seed_default_schemas(tenant)`)
chamada tanto por `seed_data.py` (primeiro seed) quanto por `_provision_tenant` (todo
tenant novo).

## Status

**RESOLVIDO** (branch `018-fix-tenant-schema-seed`, 2026-09-07 — `/speckit-implement`).

O catálogo de tipos de documento (`SchemaConfig`/`LayoutConfig`) foi movido para um
**app global `catalog`** (SHARED_APPS, schema `public`): uma única cópia lida por todos
os tenants via `search_path`. Não há mais passo de provisionamento — um tenant novo
enxerga o catálogo imediatamente (teste de regressão:
`tenants/tests/test_provisioning.py::NewTenantGlobalCatalogRegressionTests`).

O que mudou:
- novo `docuparse-project/backend-core/catalog/` (models, defaults, serializers, views,
  permissions, migrations `0001_initial` + `0002_seed_default_catalog`);
- fonte canônica única em `catalog/defaults.py::default_catalog_specs()` (lê
  `models/*/definition.py`) — substitui as duas listas divergentes;
- `documents/0014_drop_legacy_catalog_constraints` (não-destrutivo) +
  `documents/0015_drop_catalog_models` (destrutivo, com guarda de divergência
  `assert_only_canonical_rows` + `catalog/management/commands/check_catalog_divergence.py`);
- escrita no catálogo passou a exigir `tenants.manage` (era `models.edit`); `tenantAdmin`
  fica somente-leitura, refletido no frontend (`ExtractionPanel` → modo leitura +
  `CatalogScopeNotice`);
- código morto removido: `documents/startup.py::ensure_default_schemas`, o `try/except`
  mudo em `documents/apps.py`, o laço de seed por-tenant em `seed_data.py`.

Documentado no histórico do plano: `docs/specs/018-fix-tenant-schema-seed/`.
Ver [[Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants]].
