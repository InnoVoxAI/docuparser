import { Navigate, createBrowserRouter } from 'react-router'
import { useAuth } from '../modules/auth'
import { DocumentsRoutes } from '../modules/documents'
import { OperationsRoutes } from '../modules/operations'
import { SettingsRoutes } from '../modules/settings'
import { AdminRoutes } from '../modules/admin'
import { UploadRoutes } from '../modules/upload'
import { ErrorBoundary } from '../shared/components'
import { AppLayout } from './AppLayout'
import { NAV_ITEMS, navPath } from './navigation'

/** Landing em "/" — mesma regra do antigo estado inicial de `activeView` no monólito. */
function IndexRedirect() {
    const { hasPermission } = useAuth()
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
                { index: true, element: <IndexRedirect /> },
                ...DocumentsRoutes,
                ...UploadRoutes,
                ...OperationsRoutes,
                ...SettingsRoutes,
                ...AdminRoutes,
                { path: '*', element: <Navigate to="/" replace /> },
            ],
        },
    ])
}

export const router = createAppRouter()
