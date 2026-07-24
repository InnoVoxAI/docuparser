export { AdminRoutes } from './routes'
// `AdminRole` também é consumida por `TenantsView` (`src/main.tsx`, fora do
// escopo desta sub-fase — só `GerenciarUsuarios`/`GerenciarRoles` migram
// aqui) para tipar o combo de roles do formulário de convite por tenant;
// exportado via barrel em vez de duplicar a interface, mesmo padrão de
// dependência cruzada legítima já documentado em `contracts/module-boundaries.md`.
export type { AdminRole } from './types'
