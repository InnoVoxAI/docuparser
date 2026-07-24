# Phase 1 Data Model: Refatoração Arquitetural do Frontend

Esta feature não introduz entidades de domínio/negócio novas (nenhuma mudança
de contrato de API, FR-011). O "modelo de dados" aqui é o **modelo estrutural
do código** — a forma concreta das Key Entities descritas em `spec.md`,
usada para orientar a extração dos módulos.

## Módulo de domínio (`modules/<nome>`)

Shape de pasta por módulo (igual em todos, por `frontend_rules.md`):

```text
modules/<nome>/
├── components/     # UI do módulo; não exportado diretamente para fora
├── hooks/          # useQuery/useMutation do módulo + hooks de estado local
├── services/       # chamadas axios (queryFn/mutationFn), sem lógica de UI
├── store/          # slice Zustand, só se houver estado de cliente genuíno (Fase 4)
├── types.ts         # tipos do domínio do módulo (podem re-exportar de shared/types)
└── index.ts          # barrel — única superfície pública consumida por app/ ou outros módulos
```

**Regra de identidade**: um módulo é identificado pelo seu nome de pasta
(`auth`, `documents`, `operations`, `settings`, `admin`, `upload`). Nenhum
arquivo fora de `index.ts` é importável de outro módulo — violação bloqueada
por lint (FR-008, ver `contracts/module-boundaries.md`).

**Mapeamento módulo → origem no monólito atual** (`src/main.tsx`):

| Módulo | Componentes/hooks de origem (linhas aproximadas no `main.tsx` atual) |
|---|---|
| `auth` | `AuthContext`, `AuthProvider`, `useAuth`, `PermissionGuard`, `LoginPage`, `AcessoNaoAutorizado` |
| `documents` | `Dashboard`, `InboxView`, `ApprovedView`, `RejectedView`, `ValidationView`, `DocumentTable`, `useDocumentPage`, `ExtractedFieldsModal`, `RejectedDocumentModal`, `LangExtractPanel`, `DocumentMetadataPanel`, `FieldVersionHistoryModal` |
| `operations` | `OperationsView`, tipos `DlqStream`/`DlqSummary`/`DlqEvent` |
| `settings` | `SettingsView`, `OcrSettingsPanel`, `EmailSettingsPanel`, `WhatsAppSettingsPanel`, `IntegrationSettingsPanel`, `SchemaFieldsEditor`, `ExamplesEditor`, `ReferenceDocumentPanel`, `SchemaList`, `DeleteSchemaModal`, `ConfigList` |
| `admin` | `GerenciarUsuarios`, `GerenciarRoles` |
| `upload` | `UploadView` |
| `shared` | `Alert`, `EmptyState`, `Field`, `Metric`, `SearchInput`, `StatusBadge`, `KeyValueGrid`, `Pagination`, `ConfirmDialog`, `EmailMetadataModal`, `DocumentBlobPreview`, instâncias axios (`api`/`authApi`/`comApi`), `readError`/`asApiError`, `formatDate` |
| `app` | `App` (vira `router.tsx` + layout), `Root`/bootstrap (vira `src/app/main.tsx`), `NavButton` (vira parte do layout de navegação) |

## Rota

```ts
interface ModuleRoute {
  path: string                 // ex.: "/documents/inbox"
  permission: string            // mesmo código hoje usado em NAV_ITEMS (ex.: "inbox.view")
  element: React.ComponentType
  errorElement?: React.ComponentType  // error boundary da subárvore (FR-007)
}
```

Mapeamento 1:1 com os `NAV_ITEMS` atuais (`upload`, `inbox`, `dashboard`,
`validation`, `operations`, `settings`, `users`, `roles`) — mesmo `permission`
code, sem introduzir ou remover nenhuma permissão.

## Consulta de dados (Query Key Factory)

Uma fábrica por módulo que consome dados de servidor, seguindo o padrão já
descrito em `frontend_rules.md`:

```ts
// modules/documents/hooks/queryKeys.ts
export const documentKeys = {
  all: ['documents'] as const,
  list: (params: DocumentListParams) => [...documentKeys.all, 'list', params] as const,
  count: (statusCsv?: string) => [...documentKeys.all, 'count', statusCsv] as const,
  detail: (id: string) => [...documentKeys.all, 'detail', id] as const,
  fieldVersions: (id: string) => [...documentKeys.detail(id), 'field-versions'] as const,
}
```

Análogas para `operationsKeys` (DLQ summary/events) e `settingsKeys`
(schemas/layouts). `staleTime` explícito por `useQuery` (nenhum default global
implícito), conforme `frontend_rules.md`.

## Estado de cliente (Zustand — só onde sobrar, Fase 4)

```ts
interface ClientUiSlice {
  // Preenchido durante a Fase 4, conforme o que sobrar após a adoção do
  // TanStack Query. Não modelar preventivamente.
}
```

## Limite de erro (Error Boundary)

```ts
interface ModuleErrorBoundaryProps {
  children: React.ReactNode
}
interface ModuleErrorBoundaryState {
  hasError: boolean
  error: Error | null
}
```

Uma instância por rota de módulo (não uma única global), registrando o erro
em `componentDidCatch` e renderizando uma mensagem amigável (FR-007) — nunca
o `Error` cru.

## Regra de lint (inventário, Fase 0)

| Regra | Bloqueia |
|---|---|
| `@typescript-eslint/no-explicit-any` | Uso de `any` não justificado |
| `react-hooks/rules-of-hooks` + `exhaustive-deps` | Uso incorreto de hooks |
| `jsx-a11y/*` | Violações estáticas de acessibilidade (apoia FR-013) |
| Fronteira de módulo (`eslint-plugin-boundaries` ou `no-restricted-imports` por padrão) | Import de arquivo interno de outro módulo fora do barrel (FR-001/FR-008) |
| `max-lines` (150, componentes) | Componente acima do limite de FR-012/SC-002 |

## Cobertura de teste (FR-010)

Threshold do `@vitest/coverage-v8` configurado por diretório de módulo
(`modules/<nome>/**`) em ≥80% linha, aplicado a partir do momento em que o
módulo é extraído — não retroativo ao `main.tsx` ainda não migrado.
