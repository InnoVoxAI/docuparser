---
title: 018 Catálogo global de tipos de documento — implementação
type: note
permalink: docuparser/features/018-catalogo-global-de-tipos-de-documento-implementacao
tags:
- 018-fix-tenant-schema-seed
- catalog
- multi-tenancy
- implemented
---

## Resumo

`/speckit-implement` da spec `018-fix-tenant-schema-seed` (branch homônima, 2026-09-07).
`SchemaConfig`/`LayoutConfig` deixaram de ser por-tenant (`documents`, TENANT_APPS) e viraram
um **catálogo global** no app `catalog` (SHARED_APPS, schema `public`). Detalhes completos e
lista de arquivos em [[Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants]].

## Pontos de atenção para quem for mexer depois

- **`documents/0015_drop_catalog_models` é destrutivo e ainda não aplicado em prod.** Segue
  runbook de `docs/specs/018-fix-tenant-schema-seed/quickstart.md`: backup +
  `python manage.py check_catalog_divergence` (read-only) ANTES do deploy. A própria migração
  aborta com `RuntimeError` se um schema de tenant tiver linha fora do canônico.
- Fonte de verdade única do catálogo: `catalog/defaults.py::default_catalog_specs()` (lê
  `models/nota_fiscal/definition.py` e `models/contadeagua/definition.py`). `boleto`
  continua sem entrada — comportamento inalterado.
- Escrita nos endpoints do catálogo agora exige `tenants.manage` (antes `models.edit`).
  `CatalogPermission` em `catalog/permissions.py`. Token de serviço interno segue liberado.
- Frontend: área "Extração" de Configurações fica somente-leitura sem `tenants.manage`
  (`ExtractionPanel` → `ExtractionBuilder` vs. listagem read-only).
- `documents/0014` remove só as UniqueConstraints das tabelas legadas (não-destrutivo) —
  necessário porque Django proíbe nomes de constraint duplicados enquanto as duas cópias
  coexistem.

## Verificação

- `pytest catalog documents orchestrator users tenants` → 223 passed, 1 skipped.
- `migrate_schemas --shared` + `--tenant` rodados no devcontainer: `catalog_schemaconfig`
  (2) e `catalog_layoutconfig` (3) em `public`.
- Frontend: `vitest run src/modules/settings` verde (5), `tsc --noEmit` limpo,
  `eslint src/modules/settings` sem erros.
- Pré-existentes e NÃO relacionados: `src/__tests__/flows.test.tsx` (12) e
  `src/__tests__/pagination.test.tsx` (3) falham também no HEAD limpo.

## Relations

- implements [[Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants]]
- resolves [[Bug conhecido: tenants criados via convite não recebem SchemaConfig/LayoutConfig padrão]]
