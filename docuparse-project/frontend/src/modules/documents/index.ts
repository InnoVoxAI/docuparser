export { DocumentsRoutes } from './routes'
export { documentKeys, useDocumentsQuery, useDocumentCount, useDocumentMutations } from './hooks'
export type { ValidateDocumentInput } from './hooks'
// Não roteadas hoje (achado T012: "approved"/"rejected" não estão em NAV_ITEMS
// nem alcançáveis por navegação real) — exportadas para uso direto (testes,
// `RejectedDocumentModal` consumido por `app/AppLayout.tsx`).
export { ApprovedView } from './components/ApprovedView'
export { RejectedView } from './components/RejectedView'
export { RejectedDocumentModal } from './components/RejectedDocumentModal'
// Roteada via `DocumentsRoutes`/`ValidationRoute`, mas também exportada
// diretamente — `validation.test.tsx` renderiza o componente isolado (mesmo
// padrão de teste já usado antes da extração).
export { ValidationView } from './components/ValidationView'
