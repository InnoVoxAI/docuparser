# Quickstart — Transição para o catálogo global (018)

Runbook de deploy + validação. Assume django-tenants, `backend-core/entrypoint.sh` como
aplicador de migrações. Todos os comandos rodam via `/docuparser/run_script.sh <cmd>` no
devcontainer (injeta env + `PYTHONPATH`).

## Pré-deploy (código antigo ainda no ar)

1. **Verificar divergência** — não-destrutivo, usa os modelos antigos ainda em `documents`:
   ```
   /docuparser/run_script.sh python docuparse-project/backend-core/manage.py check_catalog_divergence
   ```
   - Exit `0` + "nenhuma divergência": todos os tenants têm exatamente o conjunto canônico → seguir.
   - Exit `≠0` + lista de `(schema, schema_id/version | layout/document_type)`: **parar**.
     Decidir com o time se a linha customizada vira item do catálogo global (adicionar a
     `catalog/defaults.py` antes do deploy) ou se é lixo (apagar no schema do tenant). Não
     prosseguir enquanto o comando não sair limpo.

   > Este comando é adicionado no mesmo PR mas funciona lendo `documents.SchemaConfig`
   > enquanto ele existir; após a migração, passa a ler `catalog.SchemaConfig` (mesma
   > allow-list). Idempotente.

2. **Backup** do banco (ou snapshot do volume Postgres). O passo `0012` é irreversível.

## Deploy

3. Subir a imagem nova. `entrypoint.sh` executa, nesta ordem:
   1. `migrate_schemas --shared` → cria `catalog_schemaconfig`/`catalog_layoutconfig` em
      `public` (`catalog/0001`) e popula os 2+3 defaults (`catalog/0002`).
   2. `migrate_schemas` (tenant) → para cada `tenant_<slug>`: `documents/0012` roda a
      verificação canônica e, se limpa, `DROP` das tabelas por-tenant.
   3. `seed_data` → no-op se o banco já estiver inicializado (guardrail existente); em banco
      novo, popula permissões/roles/tenant default e chama `seed_default_catalog()`.

   Se algum schema de tenant falhar em `0012` (divergência que passou batido no passo 1),
   o deploy aborta com `RuntimeError` nomeando o schema. Os schemas já migrados ficam OK;
   corrigir o schema apontado e re-rodar `migrate_schemas`.

## Pós-deploy — validação (mapeia Success Criteria do spec)

4. **SC-001 / SC-005** — catálogo único, sem cópia por tenant:
   ```
   # em public: deve listar 2 SchemaConfig + 3 LayoutConfig
   /docuparser/run_script.sh python docuparse-project/backend-core/manage.py shell -c \
     "from catalog.models import SchemaConfig, LayoutConfig; print(SchemaConfig.objects.count(), LayoutConfig.objects.count())"
   # nenhum schema de tenant deve ter mais as tabelas documents_schemaconfig/_layoutconfig
   ```

5. **SC-002** — tenant novo pronto sem seed:
   - Provisionar um tenant de teste via `POST /api/admin/tenants/`.
   - `GET /api/ocr/layout-configs` com JWT desse tenant → retorna os 3 layouts. Nenhum
     comando de seed executado.

6. **SC-003** — operador cria 1x, todos veem:
   - Com JWT de um usuário `admin` (platform, `tenants.manage`): `POST /api/ocr/schema-configs`
     um schema de teste.
   - `GET` com JWT de outro tenant → o schema aparece.
   - Limpar: `DELETE` o schema de teste.

7. **SC-004** — tenantAdmin não escreve:
   - Com JWT de um usuário `tenantAdmin` (tem `models.edit`, não tem `tenants.manage`):
     `POST /api/ocr/layout-configs` → **403**. `GET` → 200.

8. **SC-007** — sem falha silenciosa:
   ```
   grep -rn "ensure_default_schemas" docuparse-project/backend-core/   # → sem resultados
   grep -n "DEFAULT_SCHEMAS\|schema_context" docuparse-project/backend-core/users/management/commands/seed_data.py  # → sem resultados
   ```

9. **SC-008 / regressão** — extração de um tipo padrão num tenant que nasceu sem catálogo:
   enviar um PDF de nota fiscal nesse tenant e confirmar `EXTRACTION_COMPLETED` (o
   `_resolve_schema_for_extraction` resolve via `catalog` global).

10. Rodar a suíte:
    ```
    /docuparser/run_script.sh bash -c "cd docuparse-project/backend-core && uv run pytest catalog documents orchestrator users tenants -q"
    ```

## Rollback

O passo `0012` destrói as tabelas por-tenant. Rollback = **restore do backup** do passo 2.
Reverter só o código (sem restore) deixa o app procurando `documents_schemaconfig` em schemas
onde ela não existe mais → 500 no fluxo de extração. Portanto: rollback de código **exige**
rollback de dados.

## Documentação a atualizar no mesmo PR (FR-016)

- `docs/specs/010-multi-tenancy-schemas/data-model.md` — nota "Superseded by 018" na seção
  SchemaConfig/LayoutConfig.
- basic-memory (`docuparser`): marcar `reference/Bug conhecido...` como resolvido; mudar
  Status da nota de decisão `Catálogo global de tipos de documento...` para "implementado".
- `CLAUDE.md` bloco `<!-- SPECKIT ... -->` → apontar para `docs/specs/018-fix-tenant-schema-seed/plan.md`.
