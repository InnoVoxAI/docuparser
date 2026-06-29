# Plano de Migração do Frontend: JavaScript/JSX → TypeScript/TSX

**Projeto**: DocuParse — módulo `frontend/`
**Objetivo**: introduzir tipagem estática **preservando 100% do comportamento atual** (layout, estilos, navegação, estado, fluxos, integrações de API e UX). Nenhuma mudança funcional.
**Stack atual**: React 18 + Vite 5 + Tailwind 3, axios, lucide-react, clsx, tailwind-merge. Sem router lib, sem Redux/Zustand/React Query.

---

## Resumo executivo (leia primeiro)

A característica que define todo o plano: **o frontend é essencialmente um único arquivo monolítico** — `src/main.jsx` com **4047 linhas** contendo o contexto de autenticação, o componente raiz, todas as ~60 telas/componentes, todos os helpers e o `ReactDOM.createRoot`. O restante de `src/` são **dados puros** (schemas/prompts/rules/examples por tipo de documento) e o CSS.

Consequências diretas:

1. As estratégias "criação paralela" e "migração por módulos/domínio" **não se aplicam bem**, porque não há múltiplos arquivos de componente para migrar isoladamente — há **um** arquivo gigante. Tentar quebrá-lo durante a migração introduziria mudança estrutural e risco, violando o objetivo.
2. A abordagem segura é: **habilitar TypeScript em modo permissivo** (`allowJs`, sem `strict`), **renomear os arquivos** (`.js`→`.ts`, `.jsx`→`.tsx`) e **endurecer a tipagem incrementalmente**, sem refatorar a estrutura.
3. O risco de dependências é **baixo**: todas as libs já trazem tipos próprios e `@types/react`/`@types/react-dom` **já estão** em `devDependencies`.
4. Não há suíte de testes no frontend → a validação de regressão é **manual** (checklist na Etapa 8) + `tsc --noEmit` + build.

---

## Etapa 1 — Inventário da Estrutura Atual

### Estrutura de diretórios

```text
frontend/
├── index.html
├── package.json            # type: module; scripts dev/build/preview
├── package-lock.json
├── vite.config.js          # proxy /api → backend-core, /com → backend-com; alias @ → ./src
├── tailwind.config.js
├── postcss.config.cjs
├── .dockerignore           # (recém-criado)
├── Dockerfile
└── src/
    ├── index.css           # estilos globais + classes utilitárias (input, *-button)
    ├── main.jsx            # 4047 linhas — TODA a aplicação
    └── models/
        ├── boleto/         { schemas.js, prompts.js, rules.js, examples.js }
        ├── contadeagua/    { schemas.js, prompts.js, rules.js, examples.js }
        ├── nota_fiscal/    { schemas.js, prompts.js, rules.js, examples.js }
        └── recibo/         { schemas.js, prompts.js }
```

### Tabela de arquivos

| Arquivo | Tipo Atual | Função no Sistema | Complexidade da Migração |
|---|---|---|---|
| `src/main.jsx` (4047 LOC) | JSX | **Toda a aplicação**: AuthContext, App, ~60 componentes/telas, 3 instâncias axios, helpers, render raiz | **Muito alta** (único arquivo, muito estado e props) |
| `src/models/boleto/schemas.js` (666) | JS | Constantes de schema + `isLikelyBoletoText()` (classificador) | Média (dados + função) |
| `src/models/nota_fiscal/schemas.js` (600) | JS | Schema + classificador NF | Média |
| `src/models/contadeagua/schemas.js` (434) | JS | Schema + classificador | Média |
| `src/models/contadeagua/rules.js` (216) | JS | Regras de normalização | Baixa |
| `src/models/boleto/examples.js` (154) | JS | Exemplos few-shot | Baixa |
| `src/models/contadeagua/examples.js` (158) | JS | Exemplos few-shot | Baixa |
| `src/models/boleto/rules.js` (119) | JS | Regras de normalização | Baixa |
| `src/models/nota_fiscal/examples.js` (95) | JS | Exemplos few-shot | Baixa |
| `src/models/contadeagua/prompts.js` (82) | JS | Função de prompt por tipo | Baixa |
| `src/models/nota_fiscal/prompts.js` (65) | JS | Função de prompt | Baixa |
| `src/models/nota_fiscal/rules.js` (42) | JS | Regras | Baixa |
| `src/models/boleto/prompts.js` (40) | JS | Função de prompt | Baixa |
| `src/models/recibo/prompts.js` (10) | JS | Prompt default | Trivial |
| `src/models/recibo/schemas.js` (9) | JS | Schema default | Trivial |
| `src/index.css` (21) | CSS | Estilos globais | **Não migra** |
| `vite.config.js` | JS | Config Vite (proxy/alias) | Baixa (opcional → `.ts`) |
| `tailwind.config.js` / `postcss.config.cjs` | JS/CJS | Config de build CSS | **Não migra** (pode ficar em JS) |

### Componentes, contexts, hooks e services dentro de `main.jsx`

Tudo vive em `main.jsx`. Mapeamento das **67 declarações de topo**:

- **Contexto / estado global**: `AuthContext` (linha 111), `AuthProvider` (113), `useAuth()` (160) — único hook customizado. Não há Redux/Zustand/React Query.
- **"Services" (camada de API)**: 3 instâncias axios — `api` (`/api/ocr`), `authApi` (`/api/auth`), `comApi` (`/com/api/v1`) — linhas 39‑41; interceptor de JWT em `AuthProvider`. ~43 chamadas espalhadas.
- **Componentes raiz / layout**: `Root` (4029), `App` (293), `NavButton`, `LoginPage`, `PermissionGuard`, `AcessoNaoAutorizado`.
- **Telas (views)**: `Dashboard`, `InboxView`, `ApprovedView`, `RejectedView`, `OperationsView`, `UploadView`, `ValidationView`, `SettingsView`, `GerenciarUsuarios`, `GerenciarRoles`.
- **Componentes de domínio**: `LangExtractPanel`, `EditableFields`, `ConfirmDialog`, `FieldVersionHistoryModal`, `DocumentMetadataPanel`, `DocumentTable`, `RejectedDocumentModal`, `EmailMetadataModal`, `OcrSettingsPanel`, `EmailSettingsPanel`, `WhatsAppSettingsPanel`, `IntegrationSettingsPanel`, `SchemaFieldsEditor`, `ExamplesEditor`, `ReferenceDocumentPanel`, `DocumentPreview`, `HighlightedOcrText`, etc.
- **Componentes utilitários de UI**: `Alert`, `EmptyState`, `Field`, `Metric`, `SearchInput`, `StatusBadge`, `KeyValueGrid`, `ConfigList`, `ReadOnlyTranscription(Formatted)`, `TabHelp`, `HintPanel`, `EngineSelect`.
- **Helpers puros (sem JSX)**: `buildSearchRegex`, `filterDocuments`, `buildMetrics`, `viewTitle`, `formatDate`, `formatEditableValue`, `parseFieldEntry`, `buildLangExtractDefinition`, `buildLangExtractPreview`, `findLikelySourceLine`, `renderHighlightedText`, `normalizeSearchText`, `escapeRegExp`, `readError`, `engineLabel`.

### Rotas / navegação

Não há `react-router`. A navegação é **estado interno** em `App` (`activeView` controlado por `NAV_ITEMS` + permissões). Logado vs. não-logado é decidido por `Root` (`user ? <App/> : <LoginPage/>`). Isso **simplifica** a migração (sem tipos de rota a modelar).

---

## Etapa 2 — Classificação dos Arquivos

### Migração obrigatória (`.jsx`/`.js` com lógica → `.tsx`/`.ts`)

- `src/main.jsx` → `src/main.tsx` (contém App, contexts, hook, componentes, services).
- `src/models/**/schemas.js` → `.ts` (têm funções classificadoras além de dados).
- `src/models/**/prompts.js`, `rules.js`, `examples.js` → `.ts` (dados/funções importados pela App).

> Observação: como tudo é importado por `main.tsx`, todos os arquivos `src/**/*.js` acabam sendo "obrigatórios" para que o `tsc` cubra o grafo. Porém, com `allowJs: true` eles **podem temporariamente continuar `.js`** (ver Etapa 3).

### Migração opcional (pode permanecer JS numa fase intermediária)

- `vite.config.js` → `vite.config.ts` (recomendado, mas Vite roda em JS sem problema).
- Arquivos `src/models/**` de **dados puros** (`examples.js`, `rules.js`, `prompts.js`): com `allowJs`, podem ficar em JS até o fim e migrar por último (baixo risco).

### Não requer migração

- `src/index.css` (CSS).
- `tailwind.config.js`, `postcss.config.cjs` (config de ferramentas; podem permanecer JS/CJS).
- Assets estáticos (não há SVG/PNG dedicados em `src/` hoje).
- `index.html`.

---

## Etapa 3 — Estratégia Recomendada

### Estratégia A — Conversão direta (rename `.jsx`→`.tsx`)

- **Vantagens**: caminho mais curto; sem código duplicado; histórico git preservado (`git mv`); compatível com o monólito (um único rename principal).
- **Riscos**: o rename de `main.jsx` expõe **todos** os erros de tipo de uma vez. Mitigado com `tsconfig` permissivo (`allowJs`, `strict: false`) e endurecimento gradual.
- **Impacto operacional**: baixo — o app continua rodando; Vite compila `.tsx` nativamente.
- **Esforço**: **médio**, concentrado em tipar incrementalmente o `main.tsx`.

### Estratégia B — Criação paralela (`Button.jsx` + `Button.tsx`)

- **Vantagens**: permitiria comparar versões.
- **Riscos**: **alto** — duplicar um arquivo de 4047 linhas é impraticável e perigoso (divergência, dois pontos de verdade). Não há componentes pequenos e isolados para conviver lado a lado.
- **Impacto/Esforço**: alto e improdutivo. **Descartada.**

### Estratégia C — Migração por módulos/domínio (Auth, Documents, Settings…)

- **Vantagens**: ideal em projetos **já modularizados** em muitos arquivos.
- **Riscos**: aqui exigiria **primeiro quebrar o monólito** em módulos — uma refatoração estrutural que **altera a organização** e aumenta o risco de regressão, contrariando o objetivo de "apenas migração tecnológica".
- **Impacto/Esforço**: alto; mistura duas mudanças (split + tipagem). **Descartada para esta migração** (recomendada como trabalho **futuro e separado**, depois do TS estável).

### ✅ Recomendação

**Estratégia A (conversão direta) com tipagem incremental e `tsconfig` permissivo no início.** É a única coerente com um monólito de arquivo único e com a meta de "zero mudança funcional". A modularização por domínio (Estratégia C) fica como **fase posterior e independente**, fora do escopo desta migração.

---

## Etapa 4 — Plano de Migração (sequência passo a passo)

> Cada passo termina com `npx tsc --noEmit` verde (ou com erros conhecidos/aceitos) e o app rodando. **Commit por passo.**

1. **Instalar TypeScript e tipos**
   `npm i -D typescript` (os `@types/react` e `@types/react-dom` já existem; manter versões compatíveis com React 18).

2. **Criar `tsconfig.json` permissivo** (ver Etapa 6) com `allowJs: true`, `checkJs: false`, `strict: false`, `jsx: "react-jsx"`, `noEmit: true`, `paths` para o alias `@`.

3. **Criar `tsconfig.node.json`** para o ambiente de build (Vite) e **`src/vite-env.d.ts`** com `/// <reference types="vite/client" />` + tipagem de `ImportMetaEnv` (há `import.meta.env.VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN`).

4. **Adicionar script** `"typecheck": "tsc --noEmit"` no `package.json` e validar que **compila com `allowJs`** antes de renomear nada (baseline verde).

5. **Renomear os arquivos de dados primeiro** (menor risco): `git mv src/models/**/*.js *.ts`. Tipar os exports (constantes de schema, funções de prompt/classificador). Validar `typecheck` + build.

6. **Renomear `vite.config.js` → `vite.config.ts`** (opcional) e tipar com `defineConfig`.

7. **Renomear `src/main.jsx` → `src/main.tsx`** (`git mv`). Atualizar `index.html` (`<script src="/src/main.tsx">`). Rodar `typecheck` e **corrigir/anotar** os erros.

8. **Tipar o núcleo transversal do `main.tsx`** (afeta tudo): `AuthContext`/`AuthProvider`/`useAuth` (tipo `User`, `AuthContextValue`), as 3 instâncias axios e o `readError`. Isso destrava inferência no resto.

9. **Tipar as views e componentes de domínio** em ordem de dependência (de baixo para cima): utilitários de UI (`Alert`, `Field`, `StatusBadge`…) → componentes de domínio (`DocumentTable`, `LangExtractPanel`, `ValidationView`…) → telas → `App` → `Root`. Definir **interfaces de Props** para cada componente.

10. **Tipar os DTOs de API** (Etapa 5) num bloco de tipos no topo de `main.tsx` (ou em `src/types.ts`) e aplicar nos retornos das chamadas axios.

11. **Endurecer o `tsconfig` por etapas**: ligar `noImplicitAny` → `strictNullChecks` → `strict: true`, corrigindo a cada incremento. Parar de aceitar `.js` (`allowJs: false`) só quando todos os `models/**` estiverem em `.ts`.

12. **Limpeza final**: remover `any` desnecessários, remover `@ts-expect-error` temporários, rodar build de produção e o checklist de regressão (Etapa 8).

> Dica anti-risco: nos passos 7‑9, é aceitável usar **`// @ts-expect-error` pontuais** ou `any` temporário para manter o app rodando enquanto a tipagem avança. O importante é nunca alterar a lógica.

---

## Etapa 5 — Tipagem Necessária

> Recomenda-se um bloco de tipos em `src/types.ts` (ou no topo de `main.tsx`). Tipar a partir dos **serializers do backend** (`backend-core/documents/serializers.py`) garante fidelidade.

### Props de componentes
Cada `function X({ a, b })` ganha `interface XProps { a: TipoA; b: TipoB }` e vira `function X({ a, b }: XProps)`. Para componentes com `children`, usar `React.PropsWithChildren<...>` ou `children: React.ReactNode`. Para callbacks, tipar a assinatura completa (`onChange: (rows: FieldRow[]) => void`).

### Estados React
`useState` deve receber o tipo quando o valor inicial não o revela:
- `useState<Document | null>(null)`, `useState<FieldRow[]>([])`, `useState<SaveMessage | null>(null)`.
- Estados primitivos (`useState('')`, `useState(false)`) são inferidos — não anotar.

### Contexts
```ts
interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hasPermission: (code: string) => boolean
}
const AuthContext = createContext<AuthContextValue | null>(null)
```
`useAuth()` deve garantir não-nulo (lançar erro se usado fora do provider) para evitar `?` em todo lugar.

### Hooks customizados
Só há `useAuth` → retorna `AuthContextValue`.

### DTOs / Objetos de API / Responses do backend
Tipos espelhando os serializers (campos reais):
```ts
interface ExtractionField { value: string; confidence: number | null }
type FieldsMap = Record<string, ExtractionField | string>

interface ExtractionResult {
  schema_id: string; schema_version: string
  fields: FieldsMap; confidence: number; requires_human_validation: boolean
}
interface Document {
  id: string; status: DocumentStatus; channel: string
  original_filename: string; content_type: string
  extraction_result: ExtractionResult | null
  active_field_version_number: number | null   // adicionado na feature 007
  full_transcription?: string; metadata?: Record<string, unknown>
  // … demais campos do DocumentDetailSerializer
}
interface ExtractionFieldVersion {
  version_number: number
  source_type: 'INITIAL_EXTRACTION' | 'PROCESSING' | 'REPROCESSING' | 'MANUAL_EDIT'
  is_active: boolean; previous_version_number: number | null
  created_at: string; created_by: string | null; fields: FieldsMap
}
interface User { id: string; name?: string; email: string; permissions: string[] }
type DocumentStatus = 'RECEIVED' | 'OCR_COMPLETED' | 'EXTRACTION_COMPLETED'
  | 'VALIDATION_PENDING' | 'APPROVED' | 'REJECTED' | /* … */ string
```
Aplicar com generics do axios: `api.get<Document[]>('/documents')`, `api.put<ExtractionFieldVersion>(...)`. Modelar **estado de UI local** como `FieldRow { name: string; value: string; confidence: number | null }`.

### Modelos compartilhados (`src/models/**`)
- `*_DEFAULT_FIELDS` → tipar como `SchemaField[]` (definir `SchemaField`).
- Funções `isLikely*Text(rawText: string, threshold?: number): boolean`.
- `*PromptForDocumentType(type: string): string`.

---

## Etapa 6 — Dependências e Configuração

### `package.json`
- Adicionar devDep: `typescript` (compatível com Vite 5 / React 18, ex.: `^5.4`).
- Manter `@types/react` / `@types/react-dom` (já presentes).
- Adicionar scripts:
  ```json
  "typecheck": "tsc --noEmit",
  "build": "tsc --noEmit && vite build"
  ```
  (incluir `tsc --noEmit` no build trava regressões de tipo no CI).

### `tsconfig.json` (inicial — permissivo)
```jsonc
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "allowJs": true,          // permite .js durante a transição
    "checkJs": false,
    "strict": false,          // endurecer por etapas (ver passo 11)
    "noEmit": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }   // espelha o alias do vite.config
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### `tsconfig.node.json`
```jsonc
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

### `src/vite-env.d.ts`
```ts
/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN?: string
  readonly VITE_BACKEND_CORE_URL?: string
  readonly VITE_BACKEND_COM_URL?: string
}
interface ImportMeta { readonly env: ImportMetaEnv }
```

### `vite.config` / aliases
- O plugin `@vitejs/plugin-react` já trata `.tsx` automaticamente — **nenhuma mudança** necessária no plugin.
- Renomear para `vite.config.ts` (opcional) e manter `resolve.alias['@']`. Garantir que `tsconfig.paths` e o alias do Vite fiquem **iguais**.

### `index.html`
- Atualizar a tag `<script type="module" src="/src/main.jsx">` → `.../src/main.tsx`.

### ESLint / Prettier
- **Hoje não existem** configs de ESLint/Prettier no projeto. Não é pré-requisito da migração; **opcional** adicionar depois: `@typescript-eslint/parser` + `@typescript-eslint/eslint-plugin`. Se adicionar, começar com regras suaves para não gerar ruído (`no-explicit-any: warn`).

### Build pipeline / Docker
- O `Dockerfile` roda `npm run dev`/`vite` — **continua igual**; Vite serve `.tsx` nativamente. Garantir que `typescript` esteja em `devDependencies` antes do `npm install` da imagem.
- Lembrar do `.dockerignore` (já criado) para não copiar `node_modules` do host.

---

## Etapa 7 — Pontos de Atenção (riscos e mitigação)

| Risco | Como aparece aqui | Mitigação |
|---|---|---|
| **Uso excessivo de `any`** | Atalho para silenciar erros no `main.tsx` gigante | Permitir `any` **temporário** com `// TODO: tipar`; ligar `noImplicitAny` só no passo 11; usar `unknown` em vez de `any` em fronteiras |
| **Perda de inferência** | Anotar demais estados óbvios | Não anotar `useState('')`/`useState(false)`; anotar só union/null/arrays vazios |
| **Componentes não tipados** | 60+ componentes sem Props | Definir `interface XProps` por componente; em último caso `React.FC<XProps>` (preferir função tipada) |
| **Refs** | `useRef` em inputs/áreas de texto | `useRef<HTMLInputElement \| null>(null)` / `HTMLTextAreaElement`; cuidado com `.current` possivelmente nulo |
| **Context API** | `createContext(null)` perde tipo | Tipar `createContext<AuthContextValue \| null>` e validar no `useAuth` |
| **React Query / Zustand / Redux** | **Não usados** | Nada a fazer — estado é `useState`/Context |
| **Formulários** | Vários inputs controlados (Login, Settings, campos) | Tipar handlers: `(e: React.ChangeEvent<HTMLInputElement>) => void`; `onSubmit: React.FormEventHandler` |
| **Bibliotecas sem tipos** | axios, lucide-react, clsx, tailwind-merge | **Todas já trazem tipos** — risco baixo; nenhum `@types/*` extra necessário |
| **Integração com backend** | Respostas `any` por padrão | Tipar via generics do axios e os DTOs da Etapa 5, espelhando os serializers; tratar campos opcionais com `?`/`\| null` |
| **`fields` com formato duplo** | `parseFieldEntry` aceita escalar **ou** `{value,confidence}` | Tipar `FieldsMap = Record<string, ExtractionField \| string>` e manter `parseFieldEntry` como **type guard** |
| **Monólito expõe tudo de uma vez** | Rename de `main.jsx` gera muitos erros | `tsconfig` permissivo no início + endurecimento gradual + `@ts-expect-error` pontuais |
| **`import.meta.env`** | `VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN` | Declarar `ImportMetaEnv` em `vite-env.d.ts` |

---

## Etapa 8 — Critérios de Validação

### Build
```bash
cd frontend
npm run typecheck        # tsc --noEmit → 0 erros (ao final)
npm run build            # tsc --noEmit && vite build → bundle gerado sem erros
```
No Docker:
```bash
cd docuparse-project
docker compose build --no-cache frontend
docker compose up -d --force-recreate --renew-anon-volumes frontend
docker compose logs --tail=20 frontend     # "VITE vX ready"
```

### Lint / tipagem
```bash
npx tsc --noEmit                 # verificação de tipos (gate principal — não há ESLint hoje)
# (opcional, se ESLint for adicionado) npx eslint "src/**/*.{ts,tsx}"
```

### Execução (validação visual)
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/        # 200
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/api/ocr/health  # 200 (proxy)
```
Abrir `http://localhost:5173/` e navegar por todas as telas.

### Regressão — checklist (zero mudança funcional)

- [ ] **Login/Logout**: login com token, persistência em localStorage, logout limpa sessão; `/api/auth/me` restaura sessão.
- [ ] **Permissões/Navegação**: itens do menu aparecem conforme `permissions`; abas bloqueadas via `PermissionGuard`.
- [ ] **Dashboard**: métricas e contagens idênticas.
- [ ] **Inbox**: listagem, busca (`filterDocuments`), seleção → navegação para validação.
- [ ] **Upload**: envio de arquivo e feedback.
- [ ] **Validação**: extração (LangExtract), edição de valor, remoção e adição de campo, **Salvar Alterações** (confirmação → nova versão; 409 conflito; confiança 100% em editados), **Visualizar Histórico** (modal somente leitura), Aprovar/Rejeitar.
- [ ] **Rejeitados**: modal de detalhes, reprocessar, excluir.
- [ ] **Aprovados**: listagem.
- [ ] **Operações**: DLQ (summary/events/requeue).
- [ ] **Configurações**: OCR, Email, WhatsApp, Integrações; editor de schema/exemplos/regras; troca de template ativo.
- [ ] **Usuários/Roles**: listagem, ativar/desativar, edição.
- [ ] **Visual**: layout, espaçamentos, cores, ícones (lucide), badges e Tailwind **idênticos** (comparar antes/depois).
- [ ] **Rede**: mesmas chamadas/parâmetros para `/api/ocr`, `/api/auth`, `/com` (conferir no DevTools → Network).
- [ ] **Console**: sem novos erros/warnings de runtime.

**Critério de sucesso**: `tsc --noEmit` sem erros, `vite build` sem erros, app idêntico visual e funcionalmente, e todos os itens do checklist verdes.

---

## Resultado Esperado / Entregáveis

1. `tsconfig.json` + `tsconfig.node.json` + `src/vite-env.d.ts`.
2. `typescript` em `devDependencies`; scripts `typecheck`/`build` atualizados.
3. `src/main.tsx` (ex‑`main.jsx`) tipado; `src/models/**/*.ts` tipados; `vite.config.ts` (opcional).
4. (Opcional) `src/types.ts` com DTOs do backend.
5. App com **comportamento e visual inalterados**, validado pelo checklist.

### Ordem segura, resumida
`typescript + tsconfig (permissivo)` → `vite-env.d.ts` → `models/*.ts` → `vite.config.ts` → `main.tsx` → tipar núcleo (Auth/axios) → tipar componentes/telas → DTOs de API → endurecer `strict` por etapas → limpeza + regressão.

> **Fora do escopo (trabalho futuro):** quebrar `main.tsx` em módulos por domínio (Auth, Documents, Settings, UI) e adicionar ESLint/Prettier + testes. Fazer **depois** que o TypeScript estiver estável, como mudança separada — para não misturar refatoração estrutural com a migração de tipos.

---

## Estado Final (migração concluída)

A migração foi concluída e endurecida até **`strict: true`** com `allowJs: false`.

### Configuração TypeScript
- `tsconfig.json`: `strict: true`, `allowJs: false`, `noEmit: true`, `jsx: "react-jsx"`, `moduleResolution: "bundler"`, paths `@/*`.
- `tsconfig.node.json` cobre `vite.config.ts`/`vitest.config.ts`; `src/vite-env.d.ts` tipa `import.meta.env`.
- `npm run typecheck` (`tsc --noEmit`) e `npm run build` (`tsc --noEmit && vite build`) **verdes**.

### Tipagem
- `src/types.ts`: domínio + DTOs espelhando o backend (`Document`, `ExtractionResult`, `ExtractionField`/`FieldsMap`, `ExtractionFieldVersion`, `FieldVersionsResponse`, `User`, `AuthContextValue`, `SchemaConfig`/`LayoutConfig`, `SchemaField`/`SchemaExample`, `FieldRow`, `SaveMessage`, `ActiveView`, etc.).
- `src/models/**/*.ts`: exports tipados (`SchemaField[]`, `SchemaExample[]`, `isLikely*Text`, `*PromptForDocumentType`).
- `src/main.tsx`: contexto de auth, props de todos os componentes/telas, estados (`useState<...>`), formulários (Ocr/Email/Integration/Schema/Layout) e DTOs via generics do axios (`api.get<Document[]>`, `api.put<ExtractionFieldVersion>`, …).
- **Leitura de erros**: `ApiError`/`asApiError` centralizam o único `any` documentado para respostas de erro; todos os `catch` passam por ele.
- `any` remanescente é **pontual e documentado**: índices de payloads dinâmicos (`SchemaConfig`/`LayoutConfig`/DLQ), metadados de canal (email/whatsapp), setters genéricos de formulário e `parseFieldEntry`. Sem `// @ts-ignore`/`// @ts-expect-error`.

### Suíte de testes (Vitest + Testing Library + MSW)
- Scripts: `npm run test`, `test:run`, `coverage`.
- **23 testes** cobrindo: autenticação (login/`/me`/logout), permissões/navegação, validação 007 (salvar/409/histórico/aprovar/rejeitar/editar), Inbox (busca), Dashboard (modal de rejeição), Operações (DLQ), Configurações (saves de OCR/Email/Integrações), CRUD de Usuários/Roles e upload manual.
- Cobertura de linhas **~67%** com piso de regressão em `vitest.config.ts` (`lines/statements 65`, `branches 58`, `functions 40`). Meta aspiracional (críticos ≥90%, demais ≥80%) é por fluxo; a métrica por arquivo é diluída pelo monólito preservado (sem split, por decisão de US1).

### Fora do escopo (trabalho futuro)
Quebrar `main.tsx` por domínio e adicionar ESLint/Prettier permanecem como mudança separada, posterior à estabilização do TypeScript.
