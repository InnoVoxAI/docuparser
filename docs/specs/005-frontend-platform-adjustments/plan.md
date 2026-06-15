# Implementation Plan: Front-end e Ajustes de Plataforma

**Branch**: `005-frontend-platform-adjustments` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `docs/specs/005-frontend-platform-adjustments/spec.md`

## Summary

Cinco ajustes focados e independentes: (1) aumentar o tempo de vida do token JWT de 15 min para 12h; (2) adicionar seeding idempotente dos SchemaConfigs padrão ao startup; (3) renomear aba "OCR referencia" para "Documento" e movê-la antes de "Modelo"; (4) remover o bloco "Vincular layout ao schema" da aba de publicação; e (5) ocultar a seção "Transcrição Completa" na tela de validação — mantendo os dados intactos.

## Technical Context

**Language/Version**: Python 3.10 (backend-core), React 18 + Vite (frontend)

**Primary Dependencies**: Django 4.x, djangorestframework-simplejwt, React, axios, lucide-react

**Storage**: PostgreSQL (produção) / SQLite (dev fallback); JSONField para `SchemaConfig.definition`

**Testing**: pytest (backend); sem suite automatizada de frontend no repositório

**Target Platform**: Linux container (Docker Compose); frontend via Cloudflare Pages

**Project Type**: Web application — API Django REST + React SPA

**Performance Goals**: Não afetadas por estas mudanças; alterações são de configuração e UI

**Constraints**: Mudanças devem ser retrocompatíveis; dados existentes não devem ser alterados

**Scale/Scope**: Single tenant (tenant-demo / default) para os modelos padrão; todos os usuários autenticados são afetados pelo token lifetime

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Notas |
|-----------|--------|-------|
| I. Code Quality — funções < 50 linhas, sem código morto | ✅ PASS | Todas as alterações são pequenas e pontuais; `seed_data` adiciona ~20 linhas |
| I. Security — sem OWASP Top 10 | ✅ PASS | Aumentar token lifetime não introduz vulnerabilidade; tokens continuam sendo JWTs assinados |
| II. Testing — testes de integração para auth flows | ⚠️ ATENÇÃO | Não há suite de teste frontend; backend: o `seed_data` deve ser coberto por teste de integração |
| III. UX Consistency — estados async visíveis | ✅ PASS | Remoções visuais não afetam estados de loading/error |
| III. Terminologia consistente — "document", "extraction" | ✅ PASS | Renomear "OCR referencia" → "Documento" alinha com o glossário da constituição |
| IV. Performance — startup < 60s | ✅ PASS | Seed com `get_or_create` é O(1); sem impacto no tempo de startup |

**Gate result**: APROVADO. A única ressalva (testing) está dentro do escopo aceitável dado que o projeto não tem CI de frontend e os fluxos backend são cobertos por pytest.

## Project Structure

### Documentation (this feature)

```text
docs/specs/005-frontend-platform-adjustments/
├── plan.md              ← este arquivo
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── checklists/
│   └── requirements.md
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
docuparse-project/
├── backend-core/
│   ├── core/
│   │   └── settings.py                          ← [1] JWT token lifetime
│   └── users/
│       └── management/
│           └── commands/
│               └── seed_data.py                  ← [2] seed SchemaConfig padrão
└── frontend/
    └── src/
        └── main.jsx                              ← [3][4][5] UI changes
```

**Structure Decision**: Web application (backend + frontend separados). Todas as mudanças são cirúrgicas dentro de arquivos existentes — nenhum arquivo novo de produção é criado, exceto o management command de seed já existente.

## Implementation Phases

### Phase 1: Backend — JWT Token Lifetime (P1)

**File**: `docuparse-project/backend-core/core/settings.py`

**Change**: Linha 41 — alterar `ACCESS_TOKEN_LIFETIME` de `timedelta(minutes=15)` para `timedelta(hours=12)`.

```python
# Before
'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),

# After
'ACCESS_TOKEN_LIFETIME': timedelta(hours=12),
```

**Why this approach**: Mudança de uma linha na configuração existente do `SIMPLE_JWT`. O frontend não tem lógica de token refresh automático, portanto o token de acesso precisa durar o tempo de trabalho do usuário. O `REFRESH_TOKEN_LIFETIME` (7 dias) não precisa ser alterado.

**Validation**: Fazer login, aguardar mais de 15 min, verificar que a sessão permanece ativa.

---

### Phase 2: Backend — Seed de Modelos Padrão de Extração (P2)

**File**: `docuparse-project/backend-core/users/management/commands/seed_data.py`

**Change**: Adicionar bloco de seeding de `SchemaConfig` ao final do método `handle()`, após a criação do tenant default.

```python
# Ao final do método handle(), após criação do tenant e do admin user:
from documents.models import SchemaConfig

DEFAULT_SCHEMAS = [
    {
        "schema_id": "nota_fiscal_default",
        "version": "v1",
        "definition": {
            "model_name": "NOTA FISCAL DEFAULT",
            "document_type": "nota_fiscal",
            "status": "active",
            "fields": [
                {"name": "tipo_documento", "type": "string", "required": True, "rule": "Tipo do documento fiscal."},
                {"name": "numero_nota", "type": "string", "required": True, "rule": "Numero da nota fiscal."},
                {"name": "data_emissao", "type": "date", "required": True, "rule": "Data de emissao da nota fiscal."},
                {"name": "fornecedor_nome", "type": "string", "required": True, "rule": "Razao social do fornecedor."},
                {"name": "cnpj_fornecedor", "type": "string", "required": True, "rule": "CNPJ do fornecedor; normalizar numerico."},
                {"name": "tomador_nome", "type": "string", "required": True, "rule": "Razao social do tomador."},
                {"name": "cnpj_tomador", "type": "string", "required": False, "rule": "CNPJ do tomador; normalizar numerico."},
                {"name": "valor_nota", "type": "decimal", "required": True, "rule": "Valor total da nota."},
                {"name": "valor_servico", "type": "decimal", "required": True, "rule": "Valor bruto do servico."},
                {"name": "issqn", "type": "decimal", "required": False, "rule": "Valor do ISSQN."},
                {"name": "retencao", "type": "boolean", "required": False, "rule": "True/false indicando retencao."},
            ],
        },
    },
    {
        "schema_id": "conta_agua_default",
        "version": "v1",
        "definition": {
            "model_name": "CONTA AGUA DEFAULT",
            "document_type": "conta_agua",
            "status": "active",
            "fields": [
                {"name": "tipo_documento", "type": "string", "required": True, "rule": "Tipo do documento: conta_agua."},
                {"name": "numero_documento", "type": "string", "required": False, "rule": "Numero do documento ou fatura."},
                {"name": "numero_contrato", "type": "string", "required": False, "rule": "Numero do contrato de fornecimento."},
                {"name": "data_vencimento", "type": "date", "required": True, "rule": "Data de vencimento da fatura."},
                {"name": "valor_total", "type": "decimal", "required": True, "rule": "Valor total a pagar."},
                {"name": "nome_cliente", "type": "string", "required": False, "rule": "Nome do titular da conta."},
                {"name": "cpf_cnpj_cliente", "type": "string", "required": False, "rule": "CPF ou CNPJ do cliente."},
                {"name": "endereco_imovel", "type": "string", "required": False, "rule": "Endereco do imovel fornecido."},
            ],
        },
    },
]

for schema_spec in DEFAULT_SCHEMAS:
    _, created = SchemaConfig.objects.get_or_create(
        tenant=tenant,
        schema_id=schema_spec["schema_id"],
        version=schema_spec["version"],
        defaults={"definition": schema_spec["definition"], "is_active": True},
    )
    if created:
        self.stdout.write(f"seed_data: created schema {schema_spec['schema_id']}")
    else:
        self.stdout.write(f"seed_data: schema {schema_spec['schema_id']} already exists")
```

**Why this approach**: O comando `seed_data` já é chamado no Dockerfile (`CMD`) antes do `runserver`. A constraint `UniqueConstraint(fields=["tenant", "schema_id", "version"])` garante idempotência — `get_or_create` nunca duplica. Os campos mínimos escolhidos são suficientes para o modelo aparecer na lista e ser utilizável imediatamente.

**Validation**: Após `docker compose up` em ambiente limpo, verificar que `SchemaConfig.objects.filter(schema_id__in=["nota_fiscal_default", "conta_agua_default"])` retorna 2 registros.

---

### Phase 3: Frontend — Reordenar e Renomear Abas (P3)

**File**: `docuparse-project/frontend/src/main.jsx`

**Change**: Linha ~1637 — reordenar `SETTINGS_TABS` e alterar label.

```javascript
// Before
const SETTINGS_TABS = [
    { id: 'setup', label: 'Modelo' },
    { id: 'ocr', label: 'OCR referencia' },
    ...
]

// After
const SETTINGS_TABS = [
    { id: 'ocr', label: 'Documento' },
    { id: 'setup', label: 'Modelo' },
    ...
]
```

**Also update** `SETTINGS_TAB_HELP` (linha ~1656) — a chave `'ocr'` já existe com `title: 'OCR de referencia'`; o title pode ser atualizado para `'Documento'` para manter consistência.

**Why this approach**: `SETTINGS_TABS` é um array de objetos `{id, label}`. Reordenar o array muda a ordem de renderização. A navegação `goToNextStep` usa `SETTINGS_TABS.findIndex(tab => tab.id === activeTab)`, portanto funciona independentemente da ordem. Nenhum dado é alterado.

**Validation**: Abrir Configurações → Extração e verificar que "Documento" é a primeira aba visível.

---

### Phase 4: Frontend — Remover "Vincular layout ao schema" (P4)

**File**: `docuparse-project/frontend/src/main.jsx`

**Change**: Remover o segundo `<section>` dentro de `{activeTab === 'publish' ? (...)  : null}` (linhas ~2468–2494).

```jsx
// Before (linha ~2459)
{activeTab === 'publish' ? (
    <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-md border border-zinc-200 p-4">
            {/* Salvar modelo como schema — MANTER */}
            ...
        </section>
        <section className="rounded-md border border-zinc-200 p-4">
            <div className="mb-3 text-sm font-semibold">Vincular layout ao schema</div>
            {/* ... REMOVER ESTE BLOCO INTEIRO */}
        </section>
    </div>
) : null}

// After
{activeTab === 'publish' ? (
    <div>
        <section className="rounded-md border border-zinc-200 p-4">
            {/* Salvar modelo como schema — MANTER */}
            ...
        </section>
    </div>
) : null}
```

**Note**: O wrapper `<div className="grid gap-4 xl:grid-cols-2">` pode ser simplificado para `<div>` ou mantido — com apenas um filho ele não causa layout problems.

**Why this approach**: Remoção cirúrgica do segundo `<section>`. O state `layoutForm` e a função `createLayout` não precisam ser removidos para que a feature funcione (evita análise de impacto adicional), mas podem ser removidos numa refatoração futura.

**Validation**: Abrir Configurações → Extração → Publicação e confirmar ausência do bloco "Vincular layout ao schema".

---

### Phase 5: Frontend — Ocultar "Transcrição Completa" (P5)

**File**: `docuparse-project/frontend/src/main.jsx`

**Change**: Linha ~1350 — comentar ou remover a chamada ao componente `ReadOnlyTranscription`.

```jsx
// Before (linha ~1350)
<ReadOnlyTranscription value={selectedDocument.full_transcription} />
<ReadOnlyTranscriptionFormatted value={selectedDocument.full_transcription_formatted} />

// After
{/* ReadOnlyTranscription removida visualmente — dados mantidos internamente */}
<ReadOnlyTranscriptionFormatted value={selectedDocument.full_transcription_formatted} />
```

**Why this approach**: Remover apenas a tag JSX da renderização. O componente `ReadOnlyTranscription` permanece definido no arquivo. Os dados `full_transcription` continuam sendo recebidos e armazenados — apenas não são exibidos. A seção `ReadOnlyTranscriptionFormatted` (imediatamente abaixo) permanece intocada.

**Validation**: Abrir a tela de validação de qualquer documento e confirmar: (a) "Transcrição Completa" não aparece; (b) "Transcrição Formatada" aparece normalmente.

## Complexity Tracking

Nenhuma violação da constituição identificada. Todas as mudanças são dentro dos limites de complexidade aceitos.

## Rollout Notes

- As mudanças de frontend requerem rebuild do bundle Vite e redeploy no Cloudflare Pages.
- A mudança de JWT lifetime tem efeito imediato para novos logins; tokens existentes com lifetime anterior continuam válidos até sua expiração original.
- O seed de schemas é executado automaticamente no próximo deploy (via `CMD` do Dockerfile).
- Não há migrações de banco necessárias para nenhuma das mudanças.
