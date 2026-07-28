# Quickstart: Refatoração Arquitetural do Frontend

## Ambiente

```bash
cd docuparse-project/frontend
npm install
npm run dev            # Vite dev server, proxy /api e /com conforme vite.config.ts
```

## Gate de verificação (rodar a cada etapa/commit, sem exceção)

```bash
cd docuparse-project/frontend
npm run typecheck      # tsc --noEmit
npm run lint            # inclui eslint-plugin-boundaries (fronteira de módulo) desde a Fase 5/T047
npm run test:run         # Vitest — piso: suíte de __tests__ já existente (15 arquivos / 43 testes ao final da Fase 6)
npm run build            # tsc --noEmit && vite build
```

Uma etapa só é considerada concluída quando os quatro comandos acima
terminam sem erro **e** o checklist visual manual abaixo foi percorrido.

Desde a Fase 5 (T050) os três primeiros comandos também rodam automaticamente
em CI a cada push/PR que toque `docuparse-project/frontend/**`, via
`.github/workflows/frontend-ci.yaml` (pipeline próprio do frontend, separado
do pipeline de deploy dos 4 backends em `ci.yaml`).

## Checklist visual manual (regressão — reaproveitado de `TYPESCRIPT_MIGRATION.md`)

Login/logout · permissões por item de menu · Dashboard (métricas e listagem)
· Inbox (busca, paginação, navegação para validação) · Upload · Validação
(extração, edição de campo, histórico de versão, aprovar/rejeitar) ·
Rejeitados (modal, reprocessar, excluir) · Aprovados · Operações/DLQ (summary,
events, requeue) · Configurações (todas as abas) · Usuários/Roles.

> **Nota (T012/T014, 2026-07-24)**: as telas de listagem completa "Aprovados"
> (`ApprovedView`) e "Rejeitados" (`RejectedView`) existem no código mas **não
> são alcançáveis por navegação manual hoje** — nenhum item de `NAV_ITEMS` leva
> a elas e nenhum clique no app define `activeView` como `'approved'` ou
> `'rejected'`. Apenas o modal "Documento Rejeitado" (aberto ao clicar em um
> documento rejeitado no Dashboard) é alcançável manualmente — é isso que o
> item "Rejeitados (modal, reprocessar, excluir)" acima cobre. As duas telas
> de listagem completa só têm cobertura automatizada (`approved.test.tsx`,
> `rejected.test.tsx`, renderizando o componente diretamente, como já era
> feito para `ValidationView`) — não há passo manual equivalente a executar
> para "Aprovados" até que a Fase 4 conecte essas telas a uma rota real.

## Como extrair um módulo (padrão a repetir por módulo, ver `research.md` §2)

1. Criar `src/modules/<nome>/{components,hooks,services,types.ts,index.ts}`.
2. Mover o código correspondente de `src/main.tsx` para dentro do módulo,
   sem alterar comportamento (copiar, depois apagar do monólito, nunca
   reescrever "de cabeça").
3. Se o módulo busca dados de servidor: converter `useState`+`useEffect`+axios
   para `useQuery`/`useMutation` com uma fábrica de chaves em
   `hooks/queryKeys.ts` (ver `data-model.md`).
4. Se o módulo tem formulários: converter para `react-hook-form` +
   `zodResolver`, preservando as mesmas regras/mensagens de validação.
5. Exportar a superfície pública pelo `index.ts` (ver
   `contracts/module-boundaries.md`) e atualizar `src/main.tsx` (ou o router,
   se já migrado) para importar do barrel.
6. Adicionar/mover os testes correspondentes para `modules/<nome>/__tests__`
   (ou manter em `src/__tests__` se for mais simples nesta fase — não é um
   requisito bloqueante mover a localização física dos testes, apenas garantir
   cobertura ≥80% do módulo).
7. Rodar o gate de verificação completo (seção acima) + checklist visual.
8. Commit da etapa.

## Armadilhas conhecidas (descobertas durante as Fases 2–6, T053)

Não são hipotéticas — cada uma causou um problema real durante a migração e
está detalhada em `tasks.md` na nota "Resultado" da tarefa referenciada.

- **Entrypoint do Vite**: ao criar um novo arquivo de bootstrap (`src/app/main.tsx`,
  T024), `index.html` precisa apontar para ele explicitamente
  (`<script src="/src/app/main.tsx">`). Sem isso o novo bootstrap nunca roda —
  falha silenciosa (a página carrega, mas com o código antigo).
- **`eslint-plugin-boundaries` sem resolver configurado é um no-op silencioso**
  (T047): sem `settings['import/resolver']` com `node: { extensions: [...] }`
  explícito, o plugin não resolve nenhum import relativo `.ts`/`.tsx` local —
  toda dependência vira "unknown" e, como `checkUnknownLocals` é `false` por
  padrão, a regra de fronteira não verifica nada. `npm run lint` "passa limpo"
  sem checar absolutamente nenhuma fronteira. Para depurar, rodar
  `ESLINT_PLUGIN_BOUNDARIES_DEBUG=1 npx eslint <arquivo>` e inspecionar se
  `to.file.path` resolve para `null`.
- **`eslint-plugin-boundaries`: "internal" só cobre mesmo diretório, não mesmo
  módulo** (T047): um import de `modules/x/routes/*` para `modules/x/components/*`
  (mesmo módulo, subpasta diferente) não é isento automaticamente — precisa de
  regra explícita usando `captured.moduleName`.
- **`createBrowserRouter`/`RouterProvider` é um singleton ligado a
  `window.location`/`history` reais** (T022): em testes, o `jsdom` persiste
  entre `it()`s do mesmo arquivo, então um router-singleton faz um teste
  herdar a URL deixada pelo anterior. Exportar uma fábrica (`createAppRouter()`)
  e criar um router novo por `renderApp()`, resetando `window.history` junto.
- **React 19 + Tailwind v4 via `--legacy-peer-deps` pode des-hoistear
  `@testing-library/dom`** (T011), quebrando `@testing-library/user-event`
  (`ERR_MODULE_NOT_FOUND`). Corrigido declarando `@testing-library/dom` como
  devDependency explícita na versão já resolvida.
- **Ambiente sem browser/screenshot**: nenhuma sessão deste projeto teve acesso
  a um navegador real ou ferramenta de screenshot neste sandbox de dev
  container. Para etapas de extração pura (sem mudança de JSX/classes), o
  checklist visual foi substituído por diff textual linha-a-linha contra o
  código original (`git show HEAD:...`). Para etapas com mudança de
  comportamento real (roteamento em T025, shell autenticado em T046), foi
  necessário instalar Playwright + Chromium headless ad-hoc (não commitado) e
  rodar contra `npm run dev` com as chamadas de API mockadas via `page.route`
  — não depende dos 4 backends reais. Se uma sessão futura tiver acesso a
  browser real, prefira isso ao invés do Playwright ad-hoc.

## Como validar acessibilidade de um componente migrado (SC-006)

```tsx
import { render } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'vitest-axe'
expect.extend(toHaveNoViolations)

it('não tem violações de acessibilidade', async () => {
  const { container } = render(<MeuComponente />)
  expect(await axe(container)).toHaveNoViolations()
})
```

## Ordem recomendada das fases (ver `plan.md` e `research.md` para o detalhe)

Executada integralmente nesta feature (Fases 2–6 de `tasks.md`, T004–T052) —
ordem abaixo confirmada como a que de fato funcionou, sem re-trabalho:

0. Rede de segurança: ESLint + Prettier + reforço dos smoke tests.
1. Upgrades isolados: React 19, Tailwind v4.
2. Esqueleto `app/modules/shared` vazio.
3. Extração módulo a módulo: `shared/components` → `auth` → roteamento →
   `documents` → `operations` → `settings` → `admin` → `upload`.
4. Zustand só onde sobrar estado de cliente genuíno (nesta feature, nenhum
   candidato sobrou — T043 foi pulada, o outlet context do router já resolvia
   o único estado compartilhado remanescente).
5. Formulários restantes (Login/registro) com RHF+Zod.
6. Error boundaries + mapa central de mensagens de erro.
7. Limpeza final — remoção de `src/main.tsx` (T046), lint final endurecido
   com fronteira de módulo (T047) e gate de CI dedicado (T050).

**Estado final**: `src/main.tsx` não existe mais. O bootstrap é
`src/app/main.tsx`; navegação e layout autenticado vivem em `src/app/`
(`router.tsx`, `AppLayout.tsx`, `navigation.ts`); cada tela vive em
`src/modules/{auth,documents,operations,settings,admin,upload}/`, cada uma
com um barrel `index.ts` como única superfície pública (ver
`contracts/module-boundaries.md`); primitivas de UI genéricas ficam em
`src/shared/`. `TenantsView`/`TenantUsersPanel` (feature 010, multi-tenancy)
não tinham módulo próprio mapeado em `data-model.md` e acabaram em
`modules/admin/components/` — ver a nota "4i" em
`memories/features/016-frontend-architecture-refactor-phase4.md` para a
justificativa dessa decisão se for revisitar a organização de módulos.
