---
title: Bugs pré-existentes na suíte de testes (encontrados na impl. 018)
type: note
permalink: docuparser/reference/bugs-pre-existentes-na-suite-de-testes-encontrados-na-impl.-018
tags:
- bug
- testing
- pytest
- vitest
- test-isolation
- 018-fix-tenant-schema-seed
---

Bugs/limitações **pré-existentes** (não introduzidos pela spec 018) descobertos ao rodar as
suítes durante `/speckit-implement` da 018 em 2026-09-07. Registrados aqui para não serem
reinvestigados do zero e como candidatos a follow-up.

## 1. `OperationsAccessEndpointsRBACTest` é flaky (DLQ / event-bus)

`users/tests/test_rbac_enforcement.py::OperationsAccessEndpointsRBACTest` falha de forma
**não-determinística** quando roda dentro da suíte completa (`pytest users ...`):

- Rodando só o arquivo `test_rbac_enforcement.py` 2x seguidas com **código idêntico**: uma
  vez `10 passed`, outra `1 failed`.
- O subteste que falha **muda entre execuções**: já vi
  `test_all_three_roles_can_dry_run_requeue` (role=tenantAdmin) e
  `test_all_three_roles_can_read_dlq_summary_and_events` (role=operator).
- **Passa 100% em isolamento** (`pytest ...::OperationsAccessEndpointsRBACTest`).

Causa provável: vazamento de estado entre testes no `LocalJsonlEventBus` / streams de DLQ
(`publish_dead_letter` + tempdir, ou `DOCUPARSE_LOCAL_EVENT_DIR` / bus a nível de módulo).
Os testes de DLQ (`OperationsAccessEndpointsRBACTest`, `documents/tests/test_api.py::test_dlq_operation_endpoints`)
mexem em `os.environ["DOCUPARSE_EVENT_BUS"]` e `self.settings(DOCUPARSE_LOCAL_EVENT_DIR=...)`.

Impacto: a suíte backend-core fica com 1 falha intermitente. `pytest --create-db` do
conjunto `documents orchestrator catalog users tenants` deu `223 passed, 1 skipped` numa
execução e `1 failed, 222 passed` noutra — só por causa disso.

Follow-up sugerido: fixture autouse que reseta o estado do event-bus/DLQ entre testes, ou
`DOCUPARSE_LOCAL_EVENT_DIR` sempre num tempdir por-teste.

## 2. `pytest.ini` `python_classes = Test*` não coleta as classes pytest de integração

`docuparse-project/backend-core/pytest.ini` tem `python_classes = Test*`. Isso **substitui**
o default do pytest, então classes pytest-style (não `TestCase`) que não começam com `Test`
**não são coletadas** — silenciosamente, sem erro.

Afetadas (todas marcadas `@pytest.mark.tenant_db`, nunca executam):
- `tenants/tests/test_isolation.py::TenantIsolationTests`
- `tenants/tests/test_provisioning.py::TenantSchemaIsolationTests`
- (e o que a 018 tentou adicionar: `CatalogGlobalityTests`,
  `NewTenantGlobalCatalogRegressionTests`, `CheckCatalogDivergenceTenantTests` — mantidos na
  mesma convenção do repo, portanto também não coletados)

Nota: `TransactionTestCase` com django-tenants **não** é alternativa direta — dá
`CommandError: Database test_docuparse couldn't be flushed` (django-tenants + flush).

Impacto: os testes de isolamento cross-tenant e a regressão do bug original da 018
(tenant novo enxerga o catálogo) não rodam em nenhum lugar. A CI (`.github/workflows/ci.yaml`)
**nem roda pytest** — é só deploy —, então nada disso é pego automaticamente.

Follow-up sugerido: `python_classes = Test* *Tests *Test` no `pytest.ini` (ou remover a
linha e deixar o default) + verificar se as ~5 classes que passam a ser coletadas de fato
passam.

## 3. `flows.test.tsx` e `pagination.test.tsx` do frontend falham no HEAD limpo

`docuparse-project/frontend/src/__tests__/flows.test.tsx` (12 testes) e
`.../pagination.test.tsx` (3 testes) falham **no HEAD limpo** (`git stash -u` + `vitest run`),
todas no helper `navigate()` / `renderApp()` (`findAllByText(label)`). Pré-existente,
sem relação com a 018. `vitest run src/modules/settings` está verde.

## 4. Django E032 — colisão de nome de constraint ao mover modelo entre apps

Ao criar `catalog.SchemaConfig`/`LayoutConfig` com os mesmos nomes de constraint
(`unique_schema_config_version`, `unique_layout_config`) enquanto `documents.SchemaConfig`
ainda existia: `SystemCheckError ... (models.E032) constraint name '...' is not unique among
models`. Django proíbe nomes de constraint duplicados **entre modelos**, mesmo que as
tabelas fiquem em schemas Postgres diferentes — e isso trava **qualquer** `manage.py`.

Solução adotada (018): migração intermediária `documents/0014_drop_legacy_catalog_constraints`
(só `RemoveConstraint`, não-destrutiva) antes de `documents/0015_drop_catalog_models`.
Padrão a reusar sempre que mover um modelo com `UniqueConstraint`/`CheckConstraint` nomeada
entre apps mantendo o nome.

## Relations

- relates_to [[Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants]]
- relates_to [[018 Catálogo global de tipos de documento — implementação]]
