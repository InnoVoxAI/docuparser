# Data Model — Catálogo global (018)

## Modelos movidos (sem mudança de campos)

`SchemaConfig` e `LayoutConfig` saem de `documents/models.py` (TENANT_APP) e entram em
`catalog/models.py` (SHARED_APP). **Definição de campos idêntica à atual** — a migração é de
localização de schema (tenant → public), não de forma.

### `catalog.SchemaConfig`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | `UUIDField` PK | `default=uuid4`, imutável |
| `schema_id` | `CharField(128)` | id lógico do schema de extração (ex. `nota_fiscal_default`) |
| `version` | `CharField(32)` | ex. `v1` |
| `definition` | `JSONField` | definição de campos/regras de extração |
| `is_active` | `BooleanField` | default `True` |
| `created_at`/`updated_at` | timestamps | `TimeStampedModel` |

- Constraint: `UniqueConstraint(fields=["schema_id", "version"], name="unique_schema_config_version")` — **agora global** (antes era único por schema de tenant; semanticamente é o comportamento desejado).

### `catalog.LayoutConfig`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | `UUIDField` PK | |
| `layout` | `CharField(128)` | chave usada em `Document.layout` |
| `document_type` | `CharField(64)` | fallback de classificação; `""` para os defaults |
| `schema_config` | `FK → catalog.SchemaConfig` | `on_delete=PROTECT`, `related_name="layout_configs"` |
| `confidence_threshold` | `FloatField` | default `0.75` |
| `is_active` | `BooleanField` | default `True` |
| `created_at`/`updated_at` | timestamps | |

- Constraint: `UniqueConstraint(fields=["layout", "document_type"], name="unique_layout_config")` — **agora global**.

### O que NÃO muda

- `documents.Document.layout` (`CharField`) — continua string, sem FK.
- `documents.ExtractionResult.schema_id` / `schema_version` (`CharField`) — idem. **FR-015** satisfeito sem backfill.
- `documents.OCRSettings` / `EmailSettings` / `IntegrationSettings` — permanecem em `documents` (TENANT_APP), singletons por schema. Fora de escopo.

## Conjunto canônico (`catalog/defaults.py`)

Fonte única de verdade, lida de `models/*/definition.py`:

```
SchemaConfig(schema_id="nota_fiscal_default", version="v1", definition=<models.nota_fiscal.definition.EXTRACTION_DEFINITION>)
SchemaConfig(schema_id="conta_agua_default",  version="v1", definition=<models.contadeagua.definition.EXTRACTION_DEFINITION>)

LayoutConfig(layout="nota_fiscal",        document_type="", schema_config=<nota_fiscal_default>)
LayoutConfig(layout="fatura_condominio",  document_type="", schema_config=<conta_agua_default>)
LayoutConfig(layout="fatura_energia",     document_type="", schema_config=<conta_agua_default>)
```

`PROTECTED_SCHEMA_IDS = ["nota_fiscal_default", "conta_agua_default"]` → move para `catalog`
(usado em `schema_config_detail_view` para bloquear DELETE dos defaults).

## Migrações

### `catalog/migrations/0001_initial.py`
`CreateModel` para `SchemaConfig` e `LayoutConfig` (+ constraints). Roda em `public` na fase
`migrate_schemas --shared`.

### `catalog/migrations/0002_seed_default_catalog.py`
`RunPython(seed, reverse=noop)`. `seed` = `for spec in default_catalog_specs():
SchemaConfig.objects.update_or_create(schema_id=..., version=..., defaults={definition, is_active})`
e `LayoutConfig.objects.get_or_create(layout=..., document_type="", defaults={schema_config, is_active})`.
Idempotente (FR-007, FR-009). Roda em `public`.

### `documents/migrations/0012_drop_catalog_models.py`
Depende de `documents/0011_remove_tenant_fk` e `catalog/0002`. Operações, nesta ordem:
1. `RunPython(assert_only_canonical_rows, reverse=noop)` — para o schema corrente:
   - `extra_schemas = SchemaConfig.objects.exclude((schema_id,version) ∈ canonical)`
   - `extra_layouts = LayoutConfig.objects.exclude((layout,document_type) ∈ canonical)`
   - se algum não-vazio → `raise RuntimeError(f"[{connection.schema_name}] catálogo customizado detectado: {...}. Resolva antes de migrar (ver quickstart 018).")`
2. `DeleteModel("LayoutConfig")`
3. `DeleteModel("SchemaConfig")`

Roda uma vez por schema de tenant na fase `migrate_schemas` (tenant). O `raise` aborta a
migração **daquele** schema antes do `DROP TABLE` (FR-010). Como `migrate_schemas` processa
schemas em sequência numa transação por schema, um schema limpo migra e um sujo falha sem
afetar os já migrados — o runbook manda rodar a verificação global antes.

> **Reversibilidade**: as `DeleteModel` são irreversíveis na prática (dados destruídos). O
> `reverse` das `RunPython` é `noop`. Rollback = restore de backup (documentado no quickstart).

### `seed_data.py` (fresh install)
Remover o bloco `DEFAULT_SCHEMAS` / `DEFAULT_LAYOUT_CONFIGS` + o laço
`for t in Tenant.objects.filter(is_active=True): with schema_context(...)` (linhas ~167-219).
Substituir por: `from catalog.defaults import seed_default_catalog; seed_default_catalog()`
(escreve em `public`, idempotente). Chamado uma vez, sem loop de tenant.

> Na prática `catalog/0002` já popula em toda subida via `migrate_schemas --shared`; a chamada
> em `seed_data` é defensiva para o caminho `manage.py migrate` puro (sqlite/dev) e mantém o
> "primeiro boot" auto-suficiente.

## Código morto removido (FR-005, FR-013)

| Arquivo | Remoção |
|---|---|
| `documents/startup.py` | função `ensure_default_schemas()` inteira |
| `documents/apps.py` | bloco `try: … ensure_default_schemas() … except Exception: pass` |
| `users/management/commands/seed_data.py` | bloco de seed por-tenant (~167-219) |
| `documents/views.py` | 4 views do catálogo (movidos p/ `catalog/views.py`) |
| `documents/urls.py` | 3 `path(...)` do catálogo (movidos p/ `catalog/urls.py`) |
| `documents/serializers.py` | `SchemaConfigSerializer`, `LayoutConfigSerializer` (movidos) |

## Imports a reapontar (`documents.models` → `catalog.models`)

`documents/services/ocr_processor.py`, `documents/views.py` (resto), `documents/serializers.py`,
e testes: `documents/tests/{test_api,test_models,test_process_dashboard_api}.py`,
`orchestrator/tests/test_document_pipeline_integration.py`,
`users/tests/test_rbac_enforcement.py`.
