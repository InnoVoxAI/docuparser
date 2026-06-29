# Verificação de efetividade da checagem de tipos (SC-003 / T013)

A validação estática **não é decorativa** — `tsc --noEmit` reporta erros reais.

## Como reproduzir

1. Introduzir um erro de tipo deliberado (ex.: ao final de `src/main.tsx`):
   ```ts
   const __typecheck_probe: number = "not a number"
   ```
2. Rodar a checagem:
   ```bash
   docker compose exec -T frontend npx tsc --noEmit   # ou: npm run typecheck
   ```
3. Resultado esperado (falha):
   ```
   src/main.tsx(NNNN,7): error TS2322: Type 'string' is not assignable to type 'number'.
   ```
4. Remover a linha de teste → `tsc --noEmit` volta a sair com código 0.

## Estado atual (Phase 2, modo permissivo)

- `tsconfig.json` em modo permissivo (`allowJs: true`, `strict: false`).
- `npm run typecheck` → 0 erros.
- `npm run build` (`tsc --noEmit && vite build`) → bundle gerado com sucesso.
- O endurecimento até `strict: true` ocorre nas fases US3/US4 (tasks T028–T031).
