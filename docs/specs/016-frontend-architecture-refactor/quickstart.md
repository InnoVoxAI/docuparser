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
npm run lint            # a partir da Fase 0
npm run test:run         # Vitest — piso: os 679 linhas de __tests__ já existentes
npm run build            # tsc --noEmit && vite build
```

Uma etapa só é considerada concluída quando os quatro comandos acima
terminam sem erro **e** o checklist visual manual abaixo foi percorrido.

## Checklist visual manual (regressão — reaproveitado de `TYPESCRIPT_MIGRATION.md`)

Login/logout · permissões por item de menu · Dashboard (métricas e listagem)
· Inbox (busca, paginação, navegação para validação) · Upload · Validação
(extração, edição de campo, histórico de versão, aprovar/rejeitar) ·
Rejeitados (modal, reprocessar, excluir) · Aprovados · Operações/DLQ (summary,
events, requeue) · Configurações (todas as abas) · Usuários/Roles.

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

0. Rede de segurança: ESLint + Prettier + reforço dos smoke tests.
1. Upgrades isolados: React 19, Tailwind v4.
2. Esqueleto `app/modules/shared` vazio.
3. Extração módulo a módulo: `shared/components` → `auth` → roteamento →
   `documents` → `operations` → `settings` → `admin` → `upload`.
4. Zustand só onde sobrar estado de cliente genuíno.
5. Formulários restantes (Login/registro) com RHF+Zod.
6. Error boundaries + mapa central de mensagens de erro.
7. Limpeza final — remoção de `src/main.tsx`, lint final endurecido.
