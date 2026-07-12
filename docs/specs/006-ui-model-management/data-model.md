# Data Model: Ajustes de Interface e Gerenciamento de Modelos de Extração

**Feature**: 006-ui-model-management | **Date**: 2026-06-15

---

## Entidade Afetada: SchemaConfig

A única entidade de dados afetada por esta feature é `SchemaConfig` — especificamente pela adição da operação de exclusão.

### Campos existentes (sem alterações de schema)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID (PK) | Identificador único |
| `tenant` | FK → Tenant | Tenant proprietário do schema |
| `schema_id` | CharField(128) | Identificador de negócio (ex: `nota_fiscal_default`) |
| `version` | CharField(…) | Versão do schema (ex: `v1`) |
| `definition` | JSONField | Definição completa do schema de extração |
| `is_active` | BooleanField | Indica se o schema está ativo |
| `created_at` | DateTimeField | Timestamp de criação |
| `updated_at` | DateTimeField | Timestamp de última atualização |

**Constraint existente**: `UniqueConstraint(fields=["tenant", "schema_id", "version"])`

### Operação nova: DELETE

A exclusão remove o registro permanentemente do banco. Não há soft delete.

**Regra de proteção**: SchemaConfigs com `schema_id` em `["nota_fiscal_default", "conta_agua_default"]` NÃO podem ser excluídos — o backend retorna HTTP 403.

### Impacto em entidades relacionadas

| Entidade | Relação | Impacto da exclusão do SchemaConfig |
|----------|---------|-------------------------------------|
| `LayoutConfig` | `schema_config_id` FK | Layout vinculado fica sem schema (FK nullable ou ON DELETE SET NULL — verificar constraint existente) |
| `Document` (via `extraction_result`) | Referência ao `schema_id` no JSON | Nenhum impacto — o `schema_id` é armazenado como string no resultado de extração, não como FK |

> **Nota**: A constraint FK entre `LayoutConfig` e `SchemaConfig` deve ser verificada antes da implementação. Se for `ON DELETE CASCADE`, layouts vinculados são removidos junto. Se for `ON DELETE RESTRICT`, a exclusão falha se houver layouts vinculados.

---

## Sem novas entidades

Esta feature não cria novas entidades. Todas as alterações são:
1. Operacional (nova ação DELETE em `SchemaConfig`)
2. Visual (remoção/renomeação de elementos na interface)
