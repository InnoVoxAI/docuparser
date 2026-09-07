import { Navigate, createBrowserRouter } from 'react-router'
import { useAuth } from '../modules/auth'
import { DocumentsRoutes } from '../modules/documents'
import { OperationsRoutes } from '../modules/operations'
import { ProcessesRoutes, ProcessOverviewView } from '../modules/processes'
import { SettingsRoutes } from '../modules/settings'
import { AdminRoutes } from '../modules/admin'
import { UploadRoutes } from '../modules/upload'
import { ErrorBoundary } from '../shared/components'
import { AppLayout } from './AppLayout'
import { NAV_ITEMS, navPath } from './navigation'

/**
 * Landing em "/" — a Visão Geral de Processos é a página inicial pra quem
 * opera documentos (`inbox.view`/`operations.access`). Quem não tem nenhuma
 * das duas (ex.: admin de plataforma só com `tenants.manage`) cai na primeira
 * tela permitida, como no comportamento antigo.
 */
function IndexRoute() {
    const { hasPermission } = useAuth()
    if (hasPermission('inbox.view') || hasPermission('operations.access')) {
        return <ProcessOverviewView />
    }
    const target = NAV_ITEMS.find((item) => hasPermission(item.permission))?.id ?? 'dashboard'
    return <Navigate to={navPath(target)} replace />
}

/**
 * Fábrica em vez de instância única: `createBrowserRouter` liga-se ao
 * `window.location`/`history` reais no momento em que é chamado. Em testes,
 * cada `renderApp()` precisa de um router novo (ver `src/__tests__/utils.tsx`)
 * para não herdar a rota deixada pelo teste anterior no mesmo `jsdom`.
 */
export function createAppRouter() {
    return createBrowserRouter([
        {
            path: '/',
            element: <AppLayout />,
            errorElement: <ErrorBoundary />,
            children: [
                { index: true, element: <IndexRoute /> },
                ...DocumentsRoutes,
                ...UploadRoutes,
                ...OperationsRoutes,
                ...ProcessesRoutes,
                ...SettingsRoutes,
                ...AdminRoutes,
                { path: '*', element: <Navigate to="/" replace /> },
            ],
        },
    ])
}

export const router = createAppRouter()
