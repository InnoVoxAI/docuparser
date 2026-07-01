# Research: Ajustes de Interface e Gerenciamento de Modelos de Extração

**Feature**: 006-ui-model-management | **Date**: 2026-06-15

---

## Decision 1: Escopo das mudanças — frontend vs. backend

**Decision**: A maioria das mudanças é exclusivamente visual (frontend). O backend só precisa de uma nova ação para a funcionalidade de exclusão.

**Rationale**: As seções removidas ("Revisão da qualidade do OCR", "Checklist LangExtract", campos Tenant/Versão/Status, "Layouts existentes") são renderizações de dados já armazenados — sua remoção da UI não afeta o backend. O único item que requer backend é a exclusão de modelos (US3).

**Alternatives considered**: Criar endpoints de "soft delete" (is_active=false) em vez de DELETE real. Rejeitado porque o spec pede remoção completa e a proteção dos modelos padrão evita o risco de perda acidental dos defaults.

---

## Decision 2: Endpoint de delete de SchemaConfig

**Decision**: Adicionar `DELETE` ao `schema_config_detail_view` existente em `documents/views.py`, reutilizando o padrão já estabelecido em `document_delete_view` (linha ~205).

**Rationale**: O pattern já existe: `@api_view(["DELETE"])`, `get_object_or_404`, `object.delete()`, retorna `HTTP_204_NO_CONTENT`. Adicionar `"DELETE"` ao decorator de `schema_config_detail_view` é coerente com o padrão do projeto e requer zero scaffolding adicional.

**Alternatives considered**: Endpoint separado `/schema-configs/<uuid>/delete`. Rejeitado por desnecessário — REST padrão já suporta DELETE no mesmo path do recurso.

---

## Decision 3: Proteção dos modelos padrão

**Decision**: Implementar a proteção na camada do frontend (verificação do `schema_id` antes de chamar a API) com validação adicional na camada do backend (retornar HTTP 403 para IDs protegidos).

**Rationale**: A proteção frontend evita a requisição desnecessária e exibe mensagem imediata ao usuário (melhor UX). A proteção backend é a camada de segurança real — o frontend pode ser contornado. Os IDs protegidos são `nota_fiscal_default` e `conta_agua_default` conforme especificado (Opção A).

**Alternatives considered**: Apenas proteção no frontend. Rejeitado por ser insuficiente — qualquer chamada direta à API poderia excluir um modelo padrão.

---

## Decision 4: Componente de listagem com delete

**Decision**: Criar um novo componente `SchemaList` (substituindo o `ConfigList` na listagem de schemas) que suporta botão Excluir, modal de confirmação e estado de loading.

**Rationale**: O `ConfigList` é genérico e usado em dois lugares (schemas e layouts). Criar `SchemaList` especializado evita complexidade no genérico e isola a lógica de delete. O `ConfigList` continua servindo para "Layouts existentes" caso seja reativado no futuro.

**Alternatives considered**: Adicionar prop `onDelete` ao `ConfigList` genérico. Rejeitado para manter o `ConfigList` simples e sem lógica de negócio.

---

## Decision 5: Componente de confirmação de delete

**Decision**: Usar um modal inline simples (pattern já existente no projeto: `ExtractedFieldsModal`, `RejectedDocumentModal`) em vez de `window.confirm()`.

**Rationale**: O projeto já tem padrão de modal com backdrop + botões de confirmação/cancelamento. `window.confirm()` não segue o design system e bloqueia a thread principal.

**Alternatives considered**: `window.confirm()`. Rejeitado — inconsistente com o design do sistema e não customizável.

---

## Mapeamento de Arquivos Afetados

### Frontend — `docuparse-project/frontend/src/main.jsx`

| Alteração | Linha aprox. | Elemento |
|-----------|-------------|---------|
| Remover "Revisão da qualidade do OCR" | ~3042-3076 | `<section>` inside `ReferenceDocumentPanel` |
| Simplificar `ActiveTemplateHeader` — manter só "tipo" | ~2961-2964 | 3 `<span>` pills to remove (schema, layout, status) |
| Ocultar Field "Tenant" | ~2407-2409 | `<Field label="Tenant">` |
| Ocultar Field "Versao" | ~2410-2412 | `<Field label="Versao">` |
| Ocultar Field "Status" | ~2430-2437 | `<Field label="Status">` |
| Renomear "Schema" → "Schema (Campos)" | ~2404 | `<Field label="Schema">` |
| Remover HintPanel "Checklist LangExtract" | ~2433-2442 | `<HintPanel title="Checklist LangExtract" ...>` |
| Renomear "Schemas existentes" → "Modelos existentes" + remover version | ~2443 | `<ConfigList title="Schemas existentes" ...>` |
| Ocultar "Layouts existentes" | ~2444 | `<ConfigList title="Layouts existentes" ...>` |
| Renomear "Few-shot anotados" | ~3166 | String in `ExamplesEditor` |
| Adicionar `SchemaList` com botão Excluir e modal | ~2443 | Novo componente substituindo ConfigList para schemas |

### Backend — `docuparse-project/backend-core/documents/views.py`

| Alteração | Linha aprox. | Elemento |
|-----------|-------------|---------|
| Adicionar `"DELETE"` ao `schema_config_detail_view` | ~389 | `@api_view(["GET", "PATCH"])` → `["GET", "PATCH", "DELETE"]` |
| Implementar lógica de delete com proteção dos defaults | ~404 (new block) | Handler `if request.method == "DELETE":` |
