# Quickstart — Migração do Frontend para TypeScript

Guia operacional para executar a migração com baixo risco. Diretório: `docuparse-project/frontend/`.

## Pré-requisitos

- Node 18 (mesma versão do container `node:18-alpine`). Evite usar `node_modules` instalado com outra major (incidente conhecido do Vite). `.dockerignore` já impede copiar `node_modules` do host para a imagem.

## Fase 1 — Ambiente TypeScript (sem renomear código ainda)

```bash
cd docuparse-project/frontend
npm i -D typescript            # @types/react já presentes
```
Criar:
- `tsconfig.json` (permissivo): `allowJs:true`, `checkJs:false`, `strict:false`, `jsx:"react-jsx"`, `moduleResolution:"bundler"`, `noEmit:true`, `paths: { "@/*": ["./src/*"] }`.
- `tsconfig.node.json` (composite) incluindo `vite.config.ts`.
- `src/vite-env.d.ts` com `ImportMetaEnv` (ver data-model.md).
- Scripts em `package.json`: `"typecheck": "tsc --noEmit"`, `"build": "tsc --noEmit && vite build"`.

Validar baseline (deve passar com `allowJs`): `npm run typecheck`.

## Fase 1b — Stack de testes (novo escopo)

```bash
npm i -D vitest @testing-library/react @testing-library/user-event @testing-library/jest-dom jsdom msw
```
- Adicionar bloco `test` no `vite.config.ts`: `environment: "jsdom"`, `globals: true`, `setupFiles: "./src/__tests__/setup.ts"`.
- `src/__tests__/setup.ts`: importar `@testing-library/jest-dom`; iniciar servidor MSW (`beforeAll/afterEach/afterAll`).
- `src/__tests__/mocks/handlers.ts`: handlers MSW espelhando os endpoints do contrato.
- Scripts: `"test": "vitest"`, `"test:run": "vitest run"`, `"coverage": "vitest run --coverage"`.

## Fase 2 — Migrar arquivos de suporte (`src/models/**`)

```bash
git mv src/models/boleto/schemas.js src/models/boleto/schemas.ts   # repetir p/ todos
```
Tipar exports (`*_DEFAULT_FIELDS: SchemaField[]`, `isLikely*Text(t: string, threshold?: number): boolean`, `*PromptForDocumentType(type: string): string`). `npm run typecheck` verde.

## Fase 3 — Migrar o arquivo principal

```bash
git mv src/main.jsx src/main.tsx
# ajustar index.html: <script type="module" src="/src/main.tsx">
git mv vite.config.js vite.config.ts   # opcional
```
Rodar `npm run typecheck` e tratar erros (usar `// @ts-expect-error` pontual/`any` temporário para manter o app rodando).

## Fase 4 — Tipagem progressiva (dentro de `main.tsx`)

Ordem (de baixo para cima): núcleo (`AuthContextValue`, `User`, instâncias axios, `readError`) → utilitários de UI (`Alert`, `Field`, `StatusBadge`…) → componentes de domínio (`DocumentTable`, `LangExtractPanel`, `ValidationView`…) → telas → `App`/`Root` → DTOs de API (generics axios). Tipos centralizados em `src/types.ts` (ver data-model.md).

## Fase 5 — Endurecer `strict`

`noImplicitAny` → `strictNullChecks` → `strict:true`, corrigindo a cada incremento. Manter `any` apenas pontual e **documentado**. Desligar `allowJs` quando todos os `models/**` já estiverem em `.ts`.

## Comandos de validação

```bash
cd docuparse-project/frontend
npm run typecheck     # 0 erros bloqueantes (strict ao final)
npm run test:run      # suíte automatizada 100% verde
npm run coverage      # cobertura dos fluxos (críticos ≥90%, demais ≥80%)
npm run build         # tsc --noEmit && vite build → bundle gerado
```
Docker:
```bash
cd docuparse-project
docker compose build --no-cache frontend
docker compose up -d --force-recreate --renew-anon-volumes frontend
docker compose logs --tail=20 frontend          # "VITE vX ready"
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/   # 200
```

## Checklist de regressão (zero mudança funcional)

- [ ] Todas as telas montam e exibem os mesmos elementos (Login→Roles).
- [ ] Permissões/navegação idênticas por perfil.
- [ ] Fluxos: upload, extração, editar/remover/adicionar campo, **Salvar** (201/409/422), **Histórico** (read-only), aprovar/rejeitar, reprocessar/excluir, configurações, DLQ, usuários/roles.
- [ ] Rede: mesmos endpoints/params/payloads (conferir handlers MSW e DevTools→Network).
- [ ] Visual idêntico (layout, estilos, ícones, badges Tailwind).
- [ ] `typecheck`, `test:run`, `build` verdes; erro de tipo proposital é detectado.
- [ ] Sem novos erros no console; sem regressão de performance perceptível.

## Critério de pronto

`strict` ativo + 0 erros bloqueantes (`any` pontual documentado) · suíte automatizada 100% verde com cobertura-alvo · build e dev funcionais · checklist de regressão completo · comportamento e visual idênticos ao estado anterior.
