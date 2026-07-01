# Implementation Plan: Ajustes de Interface e Gerenciamento de Modelos de Extração

**Branch**: `006-ui-model-management` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `docs/specs/006-ui-model-management/spec.md`

## Summary

Simplificação visual da interface nos fluxos de Validação e Configurações de modelos de extração, removendo seções e campos desnecessários, ajustando nomenclaturas, e adicionando funcionalidade de exclusão de modelos com proteção dos defaults do sistema. A grande maioria das mudanças é exclusivamente no frontend (`main.jsx`); o backend requer apenas um novo handler DELETE no endpoint `/schema-configs/<uuid>`.

## Technical Context

**Language/Version**: Python 3.11 (backend Django) | JavaScript ES2022 + React 18 (frontend Vite)

**Primary Dependencies**: Django REST Framework, React, lucide-react, Axios (api client)

**Storage**: PostgreSQL — `SchemaConfig` model (`schema_id`, `version`, `definition`, `is_active`, `tenant`)

**Testing**: N/A — sem novos testes requeridos pelo spec

**Target Platform**: Web browser (SPA) + Django REST API

**Project Type**: Web application (monorepo: backend-core + frontend)

**Performance Goals**: Delete operation visible in <3 seconds (SC-003)

**Constraints**: Visual-only para 12 das 14 mudanças; apenas o delete requer novo endpoint backend

**Scale/Scope**: 1 arquivo frontend, 1 arquivo backend, 1 novo componente React

## Constitution Check

*GATE: Must pass before implementation begins.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality — funções ≤50 linhas, arquivos ≤400 linhas | ⚠️ WATCH | `main.jsx` já tem ~3900 linhas (file existente). Novas funções devem ser ≤50 linhas. O novo componente `SchemaList` e modal de confirmação são funções curtas. |
| I. Code Quality — Linting (ESLint) | ✅ | Manter zero violations; rodar build após implementação |
| I. Code Quality — No Dead Code | ✅ | Apenas remover elementos; nenhum código morto adicionado |
| II. Testing Standards | ✅ N/A | Spec não requer novos testes; nenhuma lógica de negócio nova no backend além do delete |
| III. UX Consistency — Async feedback | ✅ | Modal de confirmação + estado de loading no botão Excluir |
| III. UX Consistency — Error messages | ✅ | Mensagem clara para modelos protegidos; erro de API exibido ao usuário |
| IV. Performance — Endpoints ≤200ms | ✅ | DELETE é operação de banco simples; sem joins complexos |

**Violação justificada**: `main.jsx` excede 400 linhas por ser um arquivo legado grande. A feature não aumenta o problema; as adições são incrementais e mínimas.

## Project Structure

### Documentation (this feature)

```text
docs/specs/006-ui-model-management/
├── plan.md              ← este arquivo
├── spec.md
├── research.md
├── data-model.md
├── contracts/
│   └── delete-schema-config.md
└── tasks.md             ← gerado por /speckit-tasks
```

### Source Code (arquivos afetados)

```text
docuparse-project/
├── frontend/
│   └── src/
│       └── main.jsx                          ← 12 edits de UI + 2 novos componentes
└── backend-core/
    └── documents/
        └── views.py                          ← 1 edit: adicionar DELETE ao schema_config_detail_view
```

**Structure Decision**: Web application (Option 2). Mudanças concentradas em dois arquivos existentes.

## Implementation Details

### US1 — Validação Simplificada (frontend only)

**Arquivo**: `docuparse-project/frontend/src/main.jsx`

#### 1a. Remover "Revisão da qualidade do OCR"

Localização: Função `ReferenceDocumentPanel`, dentro do `activeTab === 'ocr'` block em `SettingsView`.

Remover o bloco `<section>` completo contendo:
```jsx
<div className="mb-3 text-sm font-semibold">Revisao da qualidade do OCR</div>
```
(~linhas 3042-3076)

Os estados `referenceReview` e `onReviewChange` continuam existindo para manter os dados no `buildLangExtractDefinition()` — apenas o render é removido.

#### 1b. Simplificar `ActiveTemplateHeader` — manter só "tipo"

Localização: `function ActiveTemplateHeader` (~linha 2951)

Remover as 3 pills existentes:
- `schema: {schemaForm.schema_id} · {schemaForm.version}`
- `layout: {activeLayout?.layout || layoutForm.layout || '-'}`
- `status: {schemaForm.status || '-'}`

Manter apenas:
- `tipo: {schemaForm.document_type || '-'}`

---

### US2 — Configurações de Modelo Simplificadas (frontend only)

**Arquivo**: `docuparse-project/frontend/src/main.jsx`

#### 2a. Ocultar campos Tenant, Versão, Status

Localização: `activeTab === 'setup'` block (~linhas 2399-2450)

Remover os três `<Field>` elements:
- `<Field label="Tenant">` com `<input value={schemaForm.tenant_slug} ...>`
- `<Field label="Versao">` com `<input value={schemaForm.version} ...>`
- `<Field label="Status">` com `<select value={schemaForm.status} ...>`

**Nota**: Os valores `tenant_slug`, `version` e `status` devem continuar sendo enviados ao backend via `schemaForm` state — apenas os campos visuais são removidos. Verificar que `buildLangExtractDefinition()` e `createSchema()` ainda incluem esses valores.

#### 2b. Renomear "Schema" → "Schema (Campos)"

```jsx
// Antes
<Field label="Schema">
// Depois  
<Field label="Schema (Campos)">
```

#### 2c. Remover HintPanel "Checklist LangExtract"

Remover o bloco `<HintPanel title="Checklist LangExtract" ...>` completo (~linhas 2433-2442).

Isso colapsa o grid `grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]` para não precisar mais das duas colunas. Simplificar para layout sem grid lateral se o HintPanel for o único conteúdo da segunda coluna.

#### 2d. Renomear "Schemas existentes" → "Modelos existentes" + remover versão

Substituir o `<ConfigList title="Schemas existentes" items={schemas} primaryKey="schema_id" secondaryKey="version" />` pelo novo componente `<SchemaList>` (detalhado em US3).

#### 2e. Ocultar "Layouts existentes"

Remover `<ConfigList title="Layouts existentes" items={layouts} primaryKey="layout" secondaryKey="document_type" />` e o `<div className="grid gap-4 lg:grid-cols-2">` wrapper se ficar com apenas um filho.

#### 2f. Renomear "Few-shot anotados" → "Exemplos (Few-shots anotados)"

Localização: `function ExamplesEditor` (~linha 3166)

```jsx
// Antes
<div className="text-sm font-semibold">Few-shot anotados</div>
// Depois
<div className="text-sm font-semibold">Exemplos (Few-shots anotados)</div>
```

---

### US3 — Exclusão de Modelos (frontend + backend)

#### Backend: Adicionar DELETE ao schema_config_detail_view

**Arquivo**: `docuparse-project/backend-core/documents/views.py`

```python
from django.db.models import ProtectedError

PROTECTED_SCHEMA_IDS = ["nota_fiscal_default", "conta_agua_default"]

@api_view(["GET", "PATCH", "DELETE"])
def schema_config_detail_view(request, schema_id):
    auth_error = _internal_token_error(request)
    if auth_error is not None:
        return auth_error
    config = get_object_or_404(SchemaConfig.objects.select_related("tenant"), id=schema_id)
    if request.method == "GET":
        return Response(SchemaConfigSerializer(config).data)
    if request.method == "DELETE":
        if config.schema_id in PROTECTED_SCHEMA_IDS:
            return Response(
                {"detail": "Este modelo é padrão do sistema e não pode ser excluído."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            config.delete()
        except ProtectedError:
            return Response(
                {"detail": "Este modelo possui layouts vinculados e não pode ser excluído."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
    # PATCH (existing logic)
    ...
```

#### Frontend: Novo componente SchemaList

**Arquivo**: `docuparse-project/frontend/src/main.jsx`

Criar `SchemaList` para substituir `ConfigList` na listagem de schemas. Responsabilidades:
- Exibe `schema.schema_id` (sem versão)
- Botão "Excluir" por item com ícone `Trash2` (já importado)
- Ao clicar: abre `DeleteSchemaModal` passando o schema selecionado
- Após confirmação: chama `api.delete('/schema-configs/${schema.id}')` e chama `onDeleted()` para refresh

Criar `DeleteSchemaModal`:
- Exibe nome do schema
- Botões "Cancelar" e "Excluir" (vermelho)
- Estado de loading durante a requisição
- Se `schema_id` in protected list: exibe mensagem informativa (sem chamar API)
- Em erro de API: exibe mensagem de erro

```jsx
const PROTECTED_SCHEMA_IDS = ['nota_fiscal_default', 'conta_agua_default']

function SchemaList({ schemas, onDeleted }) {
    const [targetSchema, setTargetSchema] = useState(null)
    return (
        <>
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">Modelos existentes</div>
                {schemas.length === 0 ? (
                    <EmptyState icon={Settings} text="Nenhuma configuracao cadastrada." />
                ) : (
                    <div className="divide-y divide-zinc-100">
                        {schemas.map((schema) => (
                            <div key={schema.id} className="flex items-center justify-between px-4 py-3">
                                <div className="text-sm font-medium">{schema.schema_id}</div>
                                <button
                                    type="button"
                                    onClick={() => setTargetSchema(schema)}
                                    className="flex items-center gap-1 rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                                >
                                    <Trash2 size={12} />
                                    Excluir
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </section>
            {targetSchema && (
                <DeleteSchemaModal
                    schema={targetSchema}
                    onClose={() => setTargetSchema(null)}
                    onDeleted={() => { setTargetSchema(null); onDeleted() }}
                />
            )}
        </>
    )
}
```

**Integração**: Onde atualmente está `<ConfigList title="Schemas existentes" ...>`, passar:
```jsx
<SchemaList schemas={schemas} onDeleted={onChanged} />
```

O `onChanged` prop já existe em `SettingsView` (recebido do pai) e faz `refreshData()`.

---

## Complexity Tracking

Nenhuma violação de constituição injustificada.

## Build Validation

Após todas as edits, rodar:
```bash
cd docuparse-project/frontend && npm run build
```
Deve completar em <10s sem erros.
