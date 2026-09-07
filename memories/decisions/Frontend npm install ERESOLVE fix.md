---
title: Frontend npm install ERESOLVE fix
type: decision
permalink: docuparser/decisions/frontend-npm-install-eresolve-fix
tags:
- frontend
- dependencies
- react19
---

## Contexto

`npm install` em `docuparse-project/frontend` falhava com `ERESOLVE` porque o projeto está em React 19 (`^19.2.8`) mas duas devDependencies ainda travavam em peers de React 18/older:

- `@testing-library/react@^14.2.1` (peer `react@^18`)
- `@testing-library/dom@^9.3.4` (peer exigido pelo testing-library/react 16)
- `lucide-react@^0.309.0` (peer `react@^16-18`)

## Decisão

Bump de versões, mantendo major line onde possível para minimizar breaking changes:

- `@testing-library/react`: `^14.2.1` → `^16.3.2` (primeira linha 16.x com peer `react@^18 || ^19` é 16.1.0+)
- `@testing-library/dom`: `^9.3.4` → `^10.4.1` (exigido como peer pelo testing-library/react 16)
- `lucide-react`: `^0.309.0` → `^0.577.0` (ficou na linha 0.x — que já suporta React 19 desde 0.400.0 — em vez de saltar para o major 1.x, que pode ter breaking changes na API de ícones)

Após o bump, `npm install` conclui com sucesso e `npm run typecheck` passa limpo.

## Testes pré-existentes quebrados (corrigidos na mesma sessão)

Ao rodar `npm run test:run` após o install funcionar, 6 testes falhavam em `src/__tests__/{screens,permissions,flows}.test.tsx` — **causa raiz não relacionada ao bump de dependências**, e sim a um drift pré-existente entre texto acentuado no código e não-acentuado nos testes (provavelmente os testes nunca rodaram com sucesso desde que o `npm install` já estava quebrado antes desta sessão):

- Componentes/nav renderizam "Validação", "Configurações", "Operações" (com acento) — ver `src/app/navigation.ts`
- Testes procuravam "Validacao", "Configuracoes", "Operacoes" (sem acento) — corrigido para usar os labels acentuados corretos
- `UserFormModal.tsx` (`src/modules/admin/components/UserFormModal.tsx`) nunca teve campo de senha — criação de usuário é só nome/email/role; senha é definida depois via fluxo de ativação (`src/modules/tenant-activation/components/ActivateAccountForm.tsx`). O teste em `flows.test.tsx` tinha uma linha órfã tentando preencher `/Senha/i` nesse modal — removida.

Resultado: `npm run test:run` → 16/16 arquivos, 49/49 testes passando. `npm run typecheck` limpo.
