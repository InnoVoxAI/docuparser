import { Navigate, createBrowserRouter, useOutletContext } from 'react-router'
import { useAuth, PermissionGuard, AcessoNaoAutorizado } from '../modules/auth'
import { DocumentsRoutes } from '../modules/documents'
import { OperationsRoutes } from '../modules/operations'
import { SettingsRoutes } from '../modules/settings'
import { AdminRoutes } from '../modules/admin'
import { ErrorBoundary } from '../shared/components'
import { AppLayout, NAV_ITEMS, navPath, UploadView, TenantsView, type AppOutletContext } from '../main'

function useAppContext(): AppOutletContext {
    return useOutletContext<AppOutletContext>()
}

/** Landing em "/" — mesma regra do antigo estado inicial de `activeView` no monólito. */
function IndexRedirect() {
    const { hasPermission } = useAuth()
    const target = NAV_ITEMS.find((item) => hasPermission(item.permission))?.id ?? 'dashboard'
    return <Navigate to={navPath(target)} replace />
}

function UploadRoute() {
    const { refreshData } = useAppContext()
    return (
        <PermissionGuard code="documents.send" fallback={<AcessoNaoAutorizado />}>
            <UploadView onUploaded={refreshData} />
        </PermissionGuard>
    )
}

function TenantsRoute() {
    return (
        <PermissionGuard code="tenants.manage" fallback={<AcessoNaoAutorizado />}>
            <TenantsView />
        </PermissionGuard>
    )
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
                { path: 'upload', element: <UploadRoute />, errorElement: <ErrorBoundary /> },
                ...OperationsRoutes,
                ...SettingsRoutes,
                ...AdminRoutes,
                { path: 'tenants', element: <TenantsRoute />, errorElement: <ErrorBoundary /> },
                { path: '*', element: <Navigate to="/" replace /> },
            ],
        },
    ])
}

export const router = createAppRouter()
