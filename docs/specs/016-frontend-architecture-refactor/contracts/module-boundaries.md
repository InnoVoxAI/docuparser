# Contrato: Fronteira e API Pública dos Módulos

Este projeto não expõe uma API externa nova (frontend-only, FR-011). O
"contrato" relevante aqui é **interno**: o que cada módulo expõe através do
seu barrel `index.ts` para ser consumido por `src/app` (router) ou por outros
módulos — e, simetricamente, o que cada módulo **não pode** importar
diretamente de outro.

## Regra geral (FR-001)

- Um módulo só pode ser consumido através do seu `modules/<nome>/index.ts`.
- `import X from '@/modules/auth/components/LoginForm'` → **inválido**.
- `import { LoginPage } from '@/modules/auth'` → **válido**.
- `shared/*` é a única exceção: qualquer módulo pode importar de
  `shared/components`, `shared/hooks`, `shared/lib`, `shared/types`,
  `shared/utils` diretamente (não é module-to-module, é a "ponte" prevista
  em `frontend_rules.md`).
- Enforcement automático via ESLint (ver `research.md` §7 e `data-model.md`
  "Regra de lint") — não é apenas uma convenção documental.

## Superfície pública por módulo (o que cada barrel deve exportar)

### `modules/auth`
```ts
export { AuthProvider, useAuth } from './context'
export { LoginPage } from './components/LoginPage'
export { PermissionGuard } from './components/PermissionGuard'
export type { AuthContextValue } from './types'
```
Consumido por: `src/app` (provider raiz, guarda de rota), todos os outros
módulos (via `useAuth`/`PermissionGuard` — permitido, pois é a API pública).

### `modules/documents`
```ts
export { DocumentsRoutes } from './routes'          // Dashboard/Inbox/Approved/Rejected/Validation
export { useDocumentsQuery, useDocumentQuery, useDocumentMutations } from './hooks'
export { documentKeys } from './hooks/queryKeys'
```
Consumido por: `src/app` (roteamento), `modules/settings` (referência de
documento em Configurações — hoje `ReferenceDocumentPanel`, se permanecer uma
dependência cross-module legítima, deve passar pelo barrel).

### `modules/operations`
```ts
export { OperationsRoutes } from './routes'
export { useDlqSummaryQuery, useDlqEventsQuery, useRequeueMutation } from './hooks'
```

### `modules/settings`
```ts
export { SettingsRoutes } from './routes'
export { useSchemasQuery, useLayoutsQuery } from './hooks'
```
Consumido por: `modules/documents` (schemas usados na tela de Validação) —
via barrel, nunca importando um painel interno de `settings` diretamente.

### `modules/admin`
```ts
export { AdminRoutes } from './routes'          // GerenciarUsuarios/GerenciarRoles
```

### `modules/upload`
```ts
export { UploadRoutes } from './routes'
```

### `shared`
```ts
// shared/components
export { Alert, EmptyState, Field, Metric, SearchInput, StatusBadge, KeyValueGrid, Pagination, ConfirmDialog } from './components'
// shared/lib
export { api, authApi, comApi, queryClient } from './lib'
// shared/utils
export { readError, formatDate, errorMessages } from './utils'
// shared/types
export type { Document, ExtractionResult, Paginated, User, ... } from './types'
```

## Regra de dependência entre módulos

- `documents` e `settings` têm uma dependência cruzada legítima hoje
  (Validação usa `schemas`; Configurações referencia um documento de
  exemplo). Isso é **permitido**, desde que passe pelo barrel de cada um —
  não é uma violação de FR-001, é exatamente o caso de uso que o barrel
  existe para resolver.
- Nenhum módulo de domínio pode importar de `app/*` (a dependência é sempre
  `app` → `modules/*`, nunca o inverso) — evita acoplamento circular entre o
  shell e os domínios.
