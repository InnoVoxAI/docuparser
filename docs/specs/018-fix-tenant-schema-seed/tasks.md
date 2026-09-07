---
description: "Task list — 018 Catálogo global de tipos de documento"
---

# Tasks: Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants

**Input**: `docs/specs/018-fix-tenant-schema-seed/` — plan.md, spec.md, research.md, data-model.md, contracts/catalog-endpoints.md, quickstart.md

**Tests**: incluídos. A constituição §II exige teste de regressão para todo bug reportado e
testes de contrato para mudanças de contrato entre serviços / de permissão.

**Organização**: por user story. Convenções de path — backend: `docuparse-project/backend-core/`,
frontend: `docuparse-project/frontend/src/`. Rodar comandos via `/docuparser/run_script.sh <cmd>`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizável (arquivos distintos, sem dependência pendente)
- **[Story]**: US1..US4 conforme spec.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: esqueleto do app `catalog` e fiação de URLs, sem lógica ainda.

- [X] T001 Criar esqueleto do app em `docuparse-project/backend-core/catalog/__init__.py` e `docuparse-project/backend-core/catalog/apps.py` (`CatalogConfig`, `name = "catalog"`, `default_auto_field = "django.db.models.BigAutoField"`, `ready()` vazio)
- [X] T002 Registrar `"catalog"` em `SHARED_APPS` (após `"users"`) em `docuparse-project/backend-core/core/settings.py`; confirmar que `INSTALLED_APPS = list(SHARED_APPS) + list(TENANT_APPS)` continua correto e que `catalog` NÃO aparece em `TENANT_APPS`
- [X] T003 Criar `docuparse-project/backend-core/catalog/urls.py` com `urlpatterns = []` e incluí-lo em `docuparse-project/backend-core/core/urls.py` como `path("api/ocr/", include("catalog.urls"))` dentro de `urlpatterns` (rota de tenant, após os `public_urlpatterns`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: a tabela global e a fonte canônica precisam existir antes de qualquer story.

**⚠️ CRITICAL**: nenhuma US começa antes desta fase concluída.

- [X] T004 [P] Criar `docuparse-project/backend-core/catalog/models.py` com `TimeStampedModel` (abstract, local), `SchemaConfig` e `LayoutConfig` — campos idênticos aos de `documents/models.py:281-314`, incluindo `UniqueConstraint` `unique_schema_config_version` e `unique_layout_config`, e `schema_config = ForeignKey(SchemaConfig, on_delete=PROTECT, related_name="layout_configs")`
- [X] T005 [P] Criar `docuparse-project/backend-core/catalog/defaults.py`: `default_catalog_specs()` (lê `models.nota_fiscal.definition` e `models.contadeagua.definition`; retorna 2 schemas + 3 layouts conforme data-model.md), `PROTECTED_SCHEMA_IDS = ["nota_fiscal_default", "conta_agua_default"]`, e `seed_default_catalog()` idempotente (`SchemaConfig.objects.update_or_create` por `(schema_id, version)`; `LayoutConfig.objects.get_or_create` por `(layout, document_type)`)
- [X] T006 Gerar `docuparse-project/backend-core/catalog/migrations/0001_initial.py` via `run_script.sh ... manage.py makemigrations catalog` e revisar (CreateModel x2 + constraints, sem FK a `tenants`)
- [X] T007 Criar `docuparse-project/backend-core/catalog/migrations/0002_seed_default_catalog.py` — `migrations.RunPython(seed, reverse=migrations.RunPython.noop)` onde `seed` chama `catalog.defaults.seed_default_catalog` (usando `apps.get_model`); `dependencies = [("catalog", "0001_initial")]`
- [X] T008 [P] Criar `docuparse-project/backend-core/catalog/serializers.py` — mover `SchemaConfigSerializer` e `LayoutConfigSerializer` de `documents/serializers.py` (preservar `schema_config_id = PrimaryKeyRelatedField(queryset=SchemaConfig.objects.all(), source="schema_config")` e `read_only_fields`)
- [X] T009 [P] Criar `docuparse-project/backend-core/catalog/tests/__init__.py` e `catalog/tests/test_models.py` — unicidade global das constraints, `ProtectedError` ao deletar `SchemaConfig` com `LayoutConfig` vinculado
- [X] T010 Rodar `run_script.sh ... manage.py migrate_schemas --shared` contra o Postgres do devcontainer e confirmar `catalog_schemaconfig` (2 linhas) e `catalog_layoutconfig` (3 linhas) em `public`

**Checkpoint**: catálogo global existe e está populado; tabelas antigas em `documents` ainda coexistem (aditivo, seguro).

---

## Phase 3: User Story 1 - Tenant novo já enxerga o catálogo (Priority: P1) 🎯 MVP

**Goal**: o pipeline de extração e qualquer tenant (novo ou antigo) resolvem tipos de documento a partir do catálogo global, sem passo de provisionamento.

**Independent Test**: provisionar um tenant via `POST /api/admin/tenants/` e, sem rodar seed, confirmar que `GET /api/ocr/layout-configs` (JWT do novo tenant) retorna os 3 layouts e que uma nota fiscal enviada nesse tenant chega a `EXTRACTION_COMPLETED`.

### Tests for User Story 1 ⚠️

- [X] T011 [P] [US1] Teste de regressão do bug original em `docuparse-project/backend-core/tenants/tests/test_provisioning.py` — `test_new_tenant_sees_global_catalog_without_seed`: após `_provision_tenant(...)`, dentro de `schema_context(tenant.schema_name)`, `catalog.LayoutConfig.objects.count() == 3` e nenhuma chamada de seed (marca `tenant_db`)
- [X] T012 [P] [US1] Teste de integração em `docuparse-project/backend-core/catalog/tests/test_catalog_api.py` — `test_layout_visible_across_tenants`: criar `LayoutConfig` em contexto do tenant A, ler em contexto do tenant B (marca `tenant_db`)

### Implementation for User Story 1

- [X] T013 [P] [US1] Reapontar imports em `docuparse-project/backend-core/documents/services/ocr_processor.py` (linha 16 e usos em 305, 312, 403, 406-434): `from catalog.models import LayoutConfig, SchemaConfig`
- [X] T014 [P] [US1] Reapontar imports em `docuparse-project/backend-core/documents/views.py` nas views de extração remanescentes (`process_extraction`/`extract` ~636-680, `get_object_or_404(SchemaConfig, ...)` linha 652) para `from catalog.models import SchemaConfig`
- [X] T015 [P] [US1] Reapontar imports nos testes existentes que criam `SchemaConfig`/`LayoutConfig`: `documents/tests/test_api.py`, `documents/tests/test_models.py`, `documents/tests/test_process_dashboard_api.py`, `orchestrator/tests/test_document_pipeline_integration.py` → `from catalog.models import ...`
- [X] T016 [US1] Rodar `run_script.sh bash -c "cd docuparse-project/backend-core && uv run pytest documents orchestrator catalog -q"` e deixar verde

**Checkpoint**: extração resolve via catálogo global; tenant novo funciona com zero seed.

---

## Phase 4: User Story 2 - Operador da plataforma gerencia o catálogo num único lugar (Priority: P1)

**Goal**: os endpoints do catálogo passam a ser servidos pelo app `catalog`, com escrita restrita a `tenants.manage`; `tenantAdmin` fica somente-leitura; frontend reflete isso.

**Independent Test**: com JWT `tenantAdmin` (`models.edit`, sem `tenants.manage`): `GET` 200, `POST/PATCH/DELETE` 403. Com JWT `admin` (platform): `POST` cria e o item aparece para outro tenant.

### Tests for User Story 2 ⚠️

- [X] T017 [P] [US2] Teste de contrato em `docuparse-project/backend-core/catalog/tests/test_catalog_api.py` — matriz de permissão dos 8 endpoints (contracts/catalog-endpoints.md): `tenantAdmin` GET 200 / escrita 403; `admin` POST 201; DELETE de `schema_id ∈ PROTECTED_SCHEMA_IDS` → 403; DELETE de schema com layout → 409; token de serviço → liberado
- [X] T018 [P] [US2] Atualizar `docuparse-project/backend-core/users/tests/test_rbac_enforcement.py` — import de `catalog.models`; ajustar expectativa de que `models.edit` NÃO concede mais escrita no catálogo

### Implementation for User Story 2

- [X] T019 [US2] Criar `docuparse-project/backend-core/catalog/views.py` — mover `schema_configs_view`, `schema_config_detail_view`, `layout_configs_view`, `layout_config_detail_view` de `documents/views.py` (~735-819+); importar serializers de `catalog.serializers`, `PROTECTED_SCHEMA_IDS` de `catalog.defaults`, modelos de `catalog.models`
- [X] T020 [US2] Em `catalog/views.py`, trocar as permissões: `POST`/`PATCH`/`DELETE` → `require_permission("tenants.manage")`; `GET` → `require_any_permission("models.edit", "tenants.manage")` (de `users.permissions`)
- [X] T021 [US2] Preencher `docuparse-project/backend-core/catalog/urls.py` com as 4 rotas usando as MESMAS strings de path de hoje: `schema-configs`, `schema-configs/<uuid:schema_id>`, `layout-configs`, `layout-configs/<uuid:layout_id>`
- [X] T022 [US2] Remover de `docuparse-project/backend-core/documents/views.py` as 4 views movidas e os imports agora órfãos (`LayoutConfig`, `SchemaConfig`, `LayoutConfigSerializer`, `SchemaConfigSerializer`, `ProtectedError` se não usado em outro ponto)
- [X] T023 [US2] Remover de `docuparse-project/backend-core/documents/urls.py` os imports (linhas 25, 32-33) e as rotas do catálogo (linhas 86-92)
- [X] T024 [US2] Remover `SchemaConfigSerializer` e `LayoutConfigSerializer` de `docuparse-project/backend-core/documents/serializers.py` e os imports de modelo que ficarem sem uso (linhas 14-16)
- [X] T025 [P] [US2] Frontend: em `docuparse-project/frontend/src/modules/settings/hooks/useLayoutMutations.ts` e `useSchemaMutations.ts`, remover `tenant_slug` dos tipos de input e do payload (campo morto; endpoint inalterado). Ler `docuparse-project/frontend/frontend_rules.md` antes
- [X] T026 [US2] Frontend: gatear os controles de criar/editar/excluir schema e layout em `docuparse-project/frontend/src/modules/settings/components/{SettingsView,SchemaList,ConfigList}.tsx` atrás da permissão `tenants.manage`, reusando o mesmo mecanismo de `modules/admin` (`TenantsView`); demais usuários veem o catálogo em modo leitura
- [X] T027 [P] [US2] Frontend: adicionar aviso visível "Alterações no catálogo de modelos afetam todos os tenants" próximo aos formulários de schema/layout (constituição §III)
- [X] T028 [US2] Frontend: rodar `vitest` do módulo `settings` + typecheck/lint; garantir que os testes de a11y (`__tests__/*.a11y.test.tsx`) seguem verdes
- [X] T029 [US2] Backend: rodar `pytest catalog users -q` via run_script.sh, verde

**Checkpoint**: só operador de plataforma escreve; endpoints servidos por `catalog`; frontend consistente.

---

## Phase 5: User Story 3 - Transição do ambiente atual sem perda nem duplicação (Priority: P1)

**Goal**: consolidar as cópias por-schema num único catálogo global, com verificação de divergência que aborta o passo destrutivo, e dropar as tabelas por-tenant.

**Independent Test**: rodar `migrate_schemas` num ambiente com ≥2 tenants; confirmar 1 catálogo global (2+3), nenhuma `documents_schemaconfig`/`documents_layoutconfig` remanescente, e todos os tenants ainda enviando/validando documentos padrão. Reexecutar sem erro.

### Tests for User Story 3 ⚠️

- [X] T030 [P] [US3] `docuparse-project/backend-core/catalog/tests/test_consolidation.py::test_seed_idempotent` — chamar `seed_default_catalog()` duas vezes; contagens estáveis (2 e 3), sem duplicata (FR-009)
- [X] T031 [P] [US3] `catalog/tests/test_consolidation.py::test_divergence_guard_raises` — inserir linha não-canônica num schema de tenant; asserir que o callable de guarda de `documents/0012` levanta `RuntimeError` nomeando o schema, e que `check_catalog_divergence` sai com código ≠ 0 listando a linha (marca `tenant_db`)

### Implementation for User Story 3

- [X] T032 [US3] Criar `docuparse-project/backend-core/catalog/management/commands/check_catalog_divergence.py` — read-only; itera `Tenant.objects.all()`, para cada schema faz `SELECT schema_id, version FROM documents_schemaconfig` / `SELECT layout, document_type FROM documents_layoutconfig` via `connection.cursor()` sob `schema_context`; compara com `default_catalog_specs()`; tolera tabela inexistente; imprime ofensores e `sys.exit(1)` se houver algum
- [X] T033 [US3] Remover as classes `SchemaConfig` e `LayoutConfig` de `docuparse-project/backend-core/documents/models.py` (linhas 281-314); manter `SETTINGS_SINGLETON_ID`, `TimeStampedModel` e demais modelos
- [X] T034 [US3] Criar `docuparse-project/backend-core/documents/migrations/0012_drop_catalog_models.py` — `dependencies = [("documents", "0011_remove_tenant_fk"), ("catalog", "0002_seed_default_catalog")]`; operações na ordem: (1) `RunPython(assert_only_canonical_rows, RunPython.noop)` que usa `apps.get_model("documents", "SchemaConfig"/"LayoutConfig")` + allow-list de `catalog.defaults.default_catalog_specs()` e faz `raise RuntimeError(f"[{schema_editor.connection.schema_name}] catálogo customizado: {...}")` se houver linha fora do canônico; (2) `DeleteModel("LayoutConfig")`; (3) `DeleteModel("SchemaConfig")`
- [X] T035 [US3] Rodar `run_script.sh ... manage.py migrate_schemas` (fase tenant) contra o devcontainer com ≥2 schemas; confirmar `documents_schemaconfig`/`_layoutconfig` dropadas em cada schema e catálogo global intacto (quickstart passos 3-4)
- [X] T036 [US3] Smoke de pipeline: enviar um PDF de nota fiscal num tenant que antes não tinha catálogo → `EXTRACTION_COMPLETED` (quickstart passo 9)

**Checkpoint**: catálogo único global; cópias por-tenant removidas; idempotente; guarda de divergência ativa.

---

## Phase 6: User Story 4 - Remoção do provisionamento por tenant e do código morto (Priority: P2)

**Goal**: remover (não desativar) todo mecanismo de seed por-tenant e a rotina de startup engolida por `except`.

**Independent Test**: `grep -rn "ensure_default_schemas" docuparse-project/backend-core/` vazio; `seed_data.py` sem `schema_context`; provisionar tenant não executa nenhuma etapa de tipos de documento.

- [X] T037 [US4] Remover a função `ensure_default_schemas()` inteira de `docuparse-project/backend-core/documents/startup.py` (linhas 67-102) e os imports que ficarem órfãos
- [X] T038 [US4] Remover o bloco `try: from documents.startup import ensure_default_schemas / ensure_default_schemas() / except Exception: pass` de `docuparse-project/backend-core/documents/apps.py` `ready()` (linhas 15-21); manter `log_startup_config()` e `from documents import signals`
- [X] T039 [US4] Remover o bloco de seed por-tenant de `docuparse-project/backend-core/users/management/commands/seed_data.py` (linhas ~167-219: `DEFAULT_SCHEMAS`, `DEFAULT_LAYOUT_CONFIGS`, o laço `for t in Tenant.objects.filter(is_active=True): with schema_context(...)`) e os imports locais `schema_context`, `models.contadeagua`, `models.nota_fiscal`, `documents.models`
- [X] T040 [US4] Em `seed_data.py`, na seção de schema público (após roles/permissions/tenant default), adicionar `from catalog.defaults import seed_default_catalog; seed_default_catalog()` — chamada única, sem laço de tenant
- [X] T041 [P] [US4] Criar `docuparse-project/backend-core/catalog/tests/test_no_dead_code.py` — asserir por leitura de arquivo que `documents/startup.py` não contém `ensure_default_schemas` e `seed_data.py` não contém `schema_context` (SC-007)
- [X] T042 [US4] Rodar `pytest users tenants -q` e executar `seed_data` num banco vazio (devcontainer) → catálogo populado exatamente uma vez

**Checkpoint**: nenhuma falha silenciosa; provisionamento de tenant sem etapa de catálogo.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T043 [P] Adicionar nota "**Superseded by 018** — modelos agora globais (app `catalog`, SHARED_APPS); a independência por-tenant da 010 US4 não se aplica mais a eles" em `docs/specs/010-multi-tenancy-schemas/data-model.md` §"SchemaConfig, LayoutConfig (updated)"
- [X] T044 [P] Atualizar basic-memory projeto `docuparser`: marcar `reference/Bug conhecido: tenants criados via convite não recebem SchemaConfig/LayoutConfig padrão` como resolvido (com ref do commit); mudar Status da nota `decisions/Catálogo global de tipos de documento...` para "implementado"
- [X] T045 Confirmar que o bloco `<!-- SPECKIT ... -->` em `CLAUDE.md` aponta para `docs/specs/018-fix-tenant-schema-seed/plan.md`
- [X] T046 Rodar a suíte completa do backend-core via `run_script.sh bash -c "cd docuparse-project/backend-core && uv run pytest -q"`; garantir cobertura ≥ 80% nos módulos tocados (`catalog`, `documents`) (constituição §II)
- [X] T047 Executar `docs/specs/018-fix-tenant-schema-seed/quickstart.md` passos 4-10 contra o devcontainer e registrar resultados
- [X] T048 [P] Frontend: `vitest` completo + `build`; confirmar módulo `settings` sem regressão

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup. **BLOQUEIA todas as user stories.**
- **US1 (Phase 3)** e **US2 (Phase 4)**: dependem só da Foundational; podem ser feitas em paralelo (arquivos majoritariamente distintos — US1 mexe em `ocr_processor.py`/testes de pipeline, US2 em `catalog/views.py`/`urls.py`/frontend). Ponto de contato: `documents/views.py` (T014 US1 vs T022 US2) — sequenciar T022 após T014 ou coordenar o mesmo arquivo.
- **US3 (Phase 5)**: depende de US1 **e** US2 (a `DeleteModel` em `documents/0012` só é segura depois que pipeline e endpoints já leem de `catalog`; T033 remove as classes de `documents/models.py`).
- **US4 (Phase 6)**: depende da Foundational (T040 usa `catalog.defaults`); logicamente pareada com US3 (evita duplo-seed em instalação nova). Recomendado: US4 logo após US3.
- **Polish (Phase 7)**: depois de todas as stories desejadas.

### Within Each User Story

- Testes escritos antes da implementação (devem falhar).
- Models → serializers → views → urls → frontend.
- US3: a guarda de divergência (T034 op1) precede a `DeleteModel` na própria migração.

### Parallel Opportunities

- Setup: T001 → T002 → T003 (sequencial, mesmo domínio de config).
- Foundational: T004, T005, T008, T009 em paralelo; T006 depois de T004/T005; T007 depois de T006; T010 por último.
- US1: T011, T012 (testes) em paralelo; T013, T014, T015 em paralelo entre si; T016 fecha.
- US2: T017, T018 em paralelo; T025, T027 em paralelo com o backend; T019→T020→T021 sequenciais (mesmo/encadeados arquivos de `catalog`); T022-T024 depois de T019-T021.
- US3: T030, T031 em paralelo; T032 independente; T033→T034 sequencial; T035, T036 por último.
- Polish: T043, T044, T048 em paralelo.

---

## Parallel Example: User Story 1

```bash
# Testes primeiro (devem falhar):
Task: "T011 regressão em tenants/tests/test_provisioning.py"
Task: "T012 integração cross-tenant em catalog/tests/test_catalog_api.py"

# Depois, reapontar imports em paralelo (arquivos distintos):
Task: "T013 ocr_processor.py -> catalog.models"
Task: "T014 documents/views.py (views de extração) -> catalog.models"
Task: "T015 imports nos testes de pipeline -> catalog.models"
```

---

## Implementation Strategy

### MVP (US1)

1. Phase 1 Setup → 2. Phase 2 Foundational → 3. Phase 3 US1 → **validar**: tenant novo enxerga
o catálogo e extrai sem seed. Nesse ponto o bug original já está resolvido para tenants novos
(o catálogo global existe e é lido); as cópias antigas ainda coexistem inertes.

### Entrega incremental

1. Setup + Foundational → catálogo global existe (aditivo, sem risco).
2. + US1 → pipeline e tenants novos usam o global (MVP — bug resolvido para o futuro).
3. + US2 → gestão centralizada + trava de permissão + frontend.
4. + US3 → transição destrutiva das cópias antigas (exige backup + `check_catalog_divergence`, ver quickstart).
5. + US4 → remoção do código morto de provisionamento.
6. Polish → docs normativas, memórias, suíte completa, quickstart.

### Notas

- `run_script.sh` injeta env/`PYTHONPATH` e alcança Postgres/Redis/MinIO do devcontainer — usar para tudo que toca DB/schema.
- Testes marcados `tenant_db` só rodam com `POSTGRES_HOST` setado; os demais rodam em SQLite (schema único).
- Commit por tarefa ou grupo lógico; parar em cada checkpoint para validar a story isoladamente.
- **US3 é irreversível sem restore de backup** — seguir o runbook do quickstart, não pular o passo de verificação pré-deploy.

---

## Notas de execução (`/speckit-implement`, 2026-09-07)

Todas as 48 tarefas concluídas. Desvios do plano original:

- **Numeração de migração**: `documents` já estava em `0013`, então a migração de drop virou
  **`0015_drop_catalog_models`** (não `0012`). Além disso foi necessária uma migração
  intermediária **`0014_drop_legacy_catalog_constraints`** (não-destrutiva): Django proíbe
  nomes de constraint duplicados entre `documents.SchemaConfig` e `catalog.SchemaConfig`
  durante a coexistência, então as `UniqueConstraint` legadas são removidas antes.
- **Fases 3–6 entregues juntas**: a colisão de constraint acima impede rodar qualquer
  `manage.py` com os dois conjuntos de modelos coexistindo com nomes canônicos, então o
  move de views/serializers/imports (US1/US2) e a remoção de código morto (US4) foram
  feitos no mesmo passo em vez de incrementalmente.
- **`layout-configs/<uuid>` (PATCH/DELETE)**: não existe no código hoje (só 3 rotas de
  catálogo, não 4). Mantido o contrato atual — `catalog/urls.py` tem as mesmas 3 rotas.
- **T011/T012 e testes cross-tenant**: escritos como classes pytest simples com
  `@pytest.mark.tenant_db` (mesma convenção de `tenants/tests/test_isolation.py`). O
  `pytest.ini` do repo (`python_classes = Test*`) **não coleta** essas classes — problema
  pré-existente que afeta `TenantIsolationTests` também. A cobertura de permissão (T017)
  roda via `CatalogPermissionMatrixTests` (`TestCase`).
- **T046 (suíte completa + cobertura)**: `pytest catalog documents orchestrator users
  tenants` → 223 passed, 1 skipped. `flows.test.tsx`/`pagination.test.tsx` do frontend
  falham no HEAD limpo (pré-existentes, sem relação).
- **`documents/0015` NÃO foi aplicado em produção** — é destrutivo; seguir o runbook do
  `quickstart.md` (backup + `check_catalog_divergence` pré-deploy).
