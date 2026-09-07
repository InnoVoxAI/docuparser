# Research — Catálogo global de tipos de documento (018)

Decisões técnicas para mover `SchemaConfig`/`LayoutConfig` de tenant-scoped (`documents`,
TENANT_APPS) para global (`catalog`, SHARED_APPS), com django-tenants 3.10.2.

---

## R1 — Como uma tabela pode ser global e legível de qualquer tenant

**Decision**: Criar um app Django novo `catalog` e registrá-lo em `SHARED_APPS` (antes dos
`TENANT_APPS`). Os modelos `SchemaConfig` e `LayoutConfig` vão para `catalog/models.py`.

**Rationale**: django-tenants materializa `SHARED_APPS` no schema `public`. Ao entrar num
tenant, o `PostgreSQL search_path` fica `tenant_<slug>, public` — então uma query ORM em
`catalog.SchemaConfig` de dentro de uma request de tenant resolve para a tabela em `public`
sem qualquer código especial. É exatamente como `users`, `tenants` e `auth` já funcionam
hoje (a view de documento roda em contexto de tenant e lê `Role`/`Permission` de `public`).
Escrita idem: `SchemaConfig.objects.create()` de dentro de um tenant grava em `public`.

**Alternatives considered**:
- *Manter em `documents` e adicionar camada de fallback* (ler cópia local, senão global):
  mantém duas fontes de verdade — exatamente o que o spec quer eliminar. Rejeitado.
- *View SQL / `dblink` apontando para um schema "template"*: complexidade operacional alta,
  quebra o ORM, sem ganho. Rejeitado.
- *Mover o app `documents` inteiro para SHARED_APPS*: `documents` tem `Document`,
  `ExtractionResult`, `ValidationDecision` etc. que DEVEM ser isolados por tenant. Um app é
  shared **ou** tenant, não os dois. Rejeitado.

---

## R2 — FKs e referências cruzadas ao mover os modelos

**Decision**: Mover os dois modelos juntos. Nenhuma alteração em `Document` ou
`ExtractionResult`.

**Rationale**: Levantamento das referências:
- `LayoutConfig.schema_config` → FK para `SchemaConfig` — **interna ao novo app**, migra junto.
- `Document.layout` (`CharField`) e `ExtractionResult.schema_id`/`schema_version` (`CharField`)
  — **não são FK**. Referenciam por string. Preserva FR-015 automaticamente: um documento
  processado antes da transição continua "apontando" para o mesmo `schema_id` global.
- A FK `tenant` já foi removida de ambos em `documents/0011_remove_tenant_fk` — não há
  resíduo de tenant-scoping a desfazer.
- `on_delete=PROTECT` em `LayoutConfig.schema_config` e a lógica de `ProtectedError` em
  `schema_config_detail_view` — preservadas no `catalog`.

**Alternatives considered**: adicionar FK real `Document.layout_config` durante a migração —
fora de escopo, arriscado (backfill de milhares de linhas), sem pedido. Rejeitado.

---

## R3 — Ordem das migrações no `migrate_schemas`

**Decision**: Quatro migrações + um command:
1. `catalog/0001_initial` — `CreateModel(SchemaConfig)`, `CreateModel(LayoutConfig)`. Roda em `public` (fase `--shared`).
2. `catalog/0002_seed_default_catalog` — `RunPython` idempotente que popula os 2 schemas + 3 layouts canônicos a partir de `catalog/defaults.py`. Roda em `public`.
3. `documents/0012_drop_catalog_models` — `RunPython(assert_only_canonical_rows)` **seguido de** `DeleteModel("LayoutConfig")`, `DeleteModel("SchemaConfig")`. Roda uma vez por schema de tenant (fase `--tenant`). O `RunPython` levanta `RuntimeError` com a lista de linhas divergentes → aborta a migração **antes** de qualquer `DROP TABLE` naquele schema.
4. (sem migração nova em `orchestrator`.)

**Rationale**: `entrypoint.sh` já roda `migrate_schemas --shared` **antes** de
`migrate_schemas` (tenant). Logo `catalog/0001` + `0002` (public) sempre completam antes de
`documents/0012` tocar qualquer schema de tenant — o catálogo global existe e está populado
antes de a cópia por-tenant ser destruída. Dentro do passo tenant, a verificação de
divergência roda com `connection` já no schema daquele tenant, então
`SchemaConfig.objects.all()` enxerga as linhas daquele tenant especificamente (FR-010, um
schema por vez).

**Guardrail de produção (CLAUDE.md)**: o passo destrutivo (`0012`) é auto-protegido — não
executa o `DROP` se achar divergência. Além disso o runbook (quickstart.md) manda rodar
`python manage.py check_catalog_divergence` **antes do deploy**, com o código antigo ainda
no ar, para detectar o problema sem depender do meio de um `migrate_schemas`.

**Alternatives considered**:
- *Fazer a consolidação como data migration em `documents` (RunPython copiando p/ public)*:
  data migrations em django-tenants rodam uma vez por schema; escrever em `public` de dentro
  do contexto de um tenant funciona (search_path), mas fica implícito e frágil quanto a
  ordem/idempotência entre schemas. Um `RunPython` em `catalog` (public, roda 1x) + verificação
  em `documents` (tenant, roda por schema) separa responsabilidades com clareza. Rejeitado.
- *DeleteModel sem verificação, confiando só no command pré-deploy*: viola o princípio de
  falha visível — se alguém esquecer o passo manual, perde dados de tenant silenciosamente.
  Rejeitado.

---

## R4 — Fonte de verdade canônica

**Decision**: `catalog/defaults.py` expõe uma função `default_catalog_specs()` que lê
`models.nota_fiscal.definition` e `models.contadeagua.definition` (já no `PYTHONPATH` via
`contracts`/`shared` insert em `settings.py`) e retorna a lista canônica:

| schema_id | version | layouts (layout, document_type) |
|---|---|---|
| `nota_fiscal_default` | `v1` | `("nota_fiscal", "")` |
| `conta_agua_default` | `v1` | `("fatura_condominio", "")`, `("fatura_energia", "")` |

Consumida por: `catalog/0002` (seed), `seed_data.py` (fresh install), e
`check_catalog_divergence` (allow-list para a verificação).

**Rationale**: Elimina as **duas** listas divergentes de hoje (`documents/startup.py` e
`seed_data.py` linhas ~174-190) — FR-002. Uma única definição, reusada em todo lugar.
`conta_agua_default` é o `schema_id` real usado por `contadeagua/definition.py` (confirmar no
arquivo; `PROTECTED_SCHEMA_IDS` em `views.py` lista `nota_fiscal_default` e
`conta_agua_default`).

**Nota sobre `boleto`**: `ocr_processor._classify_raw_text` referencia `models.boleto`, mas
**não existe** `SchemaConfig` seedado para boleto hoje (nem em `startup.py` nem em
`seed_data.py`). Mantém-se assim — boleto continua sem entrada no catálogo padrão; classificar
como boleto e não achar `SchemaConfig` retorna `None` (comportamento atual). Fora de escopo.

---

## R5 — Permissão: quem escreve no catálogo

**Decision**:
- Escrita (`POST`/`PATCH`/`DELETE` em `schema-configs*` e `layout-configs*`): trocar
  `require_permission("models.edit")` → `require_permission("tenants.manage")`.
- Leitura (`GET`): `require_any_permission("models.edit", "tenants.manage")` (mantém o acesso
  de quem hoje configura extração no tenant) — ou, se a UI de envio precisar, abrir para
  qualquer autenticado. **Decisão**: manter `models.edit` OR `tenants.manage` no GET; o
  pipeline usa token de serviço, que `HasDocuparsePermission` já libera (`request.auth ==
  "service_token"`).

**Rationale**: `tenants.manage` só está no role `admin` (`is_platform_role: True`) no
`seed_data.py`. `tenantAdmin` tem `models.edit`/`models.create` mas **não** `tenants.manage` —
então passa a ser leitura apenas, que é o pedido (FR-004/FR-005). Reusa o modelo de permissão
existente (nenhuma permissão nova, nenhuma migração de `Permission`/`Role`). Edge case do spec
("sem papel de plataforma configurado" → catálogo read-only para todos) sai de graça:
sem ninguém com `tenants.manage`, nenhuma escrita passa.

**Alternatives considered**:
- *Nova permissão `catalog.manage`*: mais limpo semanticamente, mas exige migração de dados
  em `Permission`/`Role` e mexer no `seed_data`/RBAC — o spec pede explicitamente para não
  mexer em papéis/permissões de 017/019. `tenants.manage` ("operador de plataforma") é
  suficiente. Rejeitado (pode virar follow-up).
- *Checar `profile.role_ref.is_platform_role` diretamente*: `is_platform_role` é um flag do
  Role, não necessariamente "pode gerir catálogo"; usar a permissão nominal é mais alinhado
  ao padrão `require_permission` do resto do código. Rejeitado.

---

## R6 — Onde ficam as rotas do catálogo

**Decision**: Mover os 4 views para `catalog/views.py` e `catalog/urls.py`, incluídas em
`core/urls.py` **sob o mesmo prefixo `/api/ocr/`** (rota de tenant). URLs finais **não mudam**:
`/api/ocr/schema-configs`, `/api/ocr/schema-configs/<uuid>`, `/api/ocr/layout-configs`,
`/api/ocr/layout-configs/<uuid>`.

**Rationale**: A leitura precisa acontecer em contexto de tenant (o frontend lista layouts
dentro da sessão do tenant, no fluxo de envio/validação). Manter sob `/api/ocr/` = zero
mudança de contrato no frontend e nos callers de serviço. A tabela ser global não exige que a
rota seja pública — `search_path` cuida disso. A permissão (`tenants.manage`) é o que garante
que só operador de plataforma escreve, independentemente de qual tenant está no JWT.

**Alternatives considered**: expor sob `/api/admin/` (rota pública, pré-resolução de tenant).
Obrigaria o frontend de settings a trocar base URL e o de envio a ter um segundo cliente.
Sem ganho. Rejeitado.

---

## R7 — Impacto no frontend

**Decision**: Mudanças mínimas no módulo `frontend/src/modules/settings`:
1. `useLayoutMutations.ts` / `useSchemaMutations.ts`: remover `tenant_slug` do input (campo
   morto — o backend nunca usou para escopo desde `0011`). Endpoints inalterados.
2. Gate de UI: botões/forms de criar/editar/excluir layout e schema só renderizam/habilitam
   quando o usuário tem `tenants.manage` (helper de permissão já usado noutros pontos do app —
   confirmar em `frontend/src/shared`). Para os demais, a tela de modelos fica read-only.
3. Cópia: aviso visível "Alterações no catálogo de modelos afetam todos os tenants" perto do
   form (constituição §III — async/estado + terminologia consistente).
4. `frontend_rules.md`: revisar antes de codar (regra do CLAUDE.md).

**Rationale**: O contrato REST não muda; o comportamento (global) muda. O risco de UX é um
`tenantAdmin` achar que edita "o seu" modelo — daí o gate + o aviso.

**Open item p/ /speckit-tasks**: confirmar se já existe helper `usePermissions()`/
`hasPermission('tenants.manage')` no frontend ou se precisa criar. (Há `TenantsView` em
`modules/admin` que já gateia por `tenants.manage` — reusar o mesmo mecanismo.)

---

## R8 — Testes

**Decision**:
- `catalog/tests/test_catalog_api.py`: (a) `tenantAdmin` recebe 200 no GET e 403 no
  POST/PATCH/DELETE; (b) `admin` (platform) consegue criar; (c) item criado por um contexto de
  tenant aparece ao consultar de outro tenant (globalidade) — marca `tenant_db`.
- `catalog/tests/test_consolidation.py`: (a) rodar `0002`/`seed` duas vezes → sem duplicata
  (idempotência, FR-009); (b) `check_catalog_divergence` retorna exit≠0 e lista a linha quando
  um schema de tenant tem `SchemaConfig` fora do canônico (FR-010); (c) `documents/0012`
  `RunPython` levanta com linha divergente.
- Regressão do bug original: `tenants/tests/test_provisioning.py` — após `_provision_tenant`,
  um GET de `layout-configs` no novo tenant retorna os 3 layouts canônicos, **sem** nenhum
  passo de seed.
- Ajustar os testes existentes que fazem `from documents.models import SchemaConfig,
  LayoutConfig` → `from catalog.models import ...` (test_api.py, test_models.py,
  test_process_dashboard_api.py, orchestrator/test_document_pipeline_integration.py,
  users/tests/test_rbac_enforcement.py).

**Rationale**: cobre cada FR testável; regressão exigida pela constituição §II.

---

## R9 — Documentação normativa a atualizar (FR-016)

**Decision**:
- `docs/specs/010-multi-tenancy-schemas/data-model.md` §"SchemaConfig, LayoutConfig (updated)":
  adicionar nota "**Superseded by 018**: estes modelos passaram a ser globais (app `catalog`,
  SHARED_APPS). A independência por-tenant citada na 010 US4 não se aplica mais a eles."
- Nota basic-memory `reference/Bug conhecido...`: marcar como **resolvida** (o replan já
  atualizou o Status; ao implementar, mudar para "resolvido em <commit>").
- Nota de decisão basic-memory `[[Catálogo global de tipos de documento...]]`: atualizar Status
  para "implementado".
- `CLAUDE.md` bloco SPECKIT: apontar para este `plan.md` durante a implementação.
- Não há arquivo `datamodel_reference.md` no repo hoje (referenciado no CLAUDE.md mas
  inexistente) — nada a fazer ali.

---

## Itens sem NEEDS CLARIFICATION

Todas as decisões de escopo foram fixadas no spec (Assumptions) antes do plano:
100% global, escrita só para operador de plataforma, sem customização de tenant em produção.
Nenhum `NEEDS CLARIFICATION` remanescente.
