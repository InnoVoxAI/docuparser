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

Documentado em `docs/specs/017-tenant-admin-onboarding/tasks.md` (T040) como débito
técnico. Não corrigido — decisão consciente de manter fora do escopo desta feature.
