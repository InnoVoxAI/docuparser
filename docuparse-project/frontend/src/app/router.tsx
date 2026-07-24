import { Navigate, createBrowserRouter, useNavigate, useOutletContext } from 'react-router'
import { useAuth, PermissionGuard, AcessoNaoAutorizado } from '../modules/auth'
import { ErrorBoundary } from '../shared/components'
import {
    AppLayout,
    NAV_ITEMS,
    navPath,
    Dashboard,
    InboxView,
    UploadView,
    ValidationView,
    OperationsView,
    SettingsView,
    GerenciarUsuarios,
    GerenciarRoles,
    TenantsView,
    type AppOutletContext,
} from '../main'

function useAppContext(): AppOutletContext {
    return useOutletContext<AppOutletContext>()
}

/** Landing em "/" — mesma regra do antigo estado inicial de `activeView` no monólito. */
function IndexRedirect() {
    const { hasPermission } = useAuth()
    const target = NAV_ITEMS.find((item) => hasPermission(item.permission))?.id ?? 'dashboard'
    return <Navigate to={navPath(target)} replace />
}

function DashboardRoute() {
    const { refreshSignal, onSelectRejected } = useAppContext()
    return (
        <PermissionGuard code="inbox.view" fallback={<AcessoNaoAutorizado />}>
            <Dashboard refreshSignal={refreshSignal} onSelectRejected={onSelectRejected} />
        </PermissionGuard>
    )
}

function InboxRoute() {
    const { refreshSignal, navigateToValidation } = useAppContext()
    const navigate = useNavigate()
    return (
        <PermissionGuard code="inbox.view" fallback={<AcessoNaoAutorizado />}>
            <InboxView
                refreshSignal={refreshSignal}
                onNavigateToValidation={navigateToValidation}
                onNavigateToUpload={() => navigate(navPath('upload'))}
            />
        </PermissionGuard>
    )
}

function UploadRoute() {
    const { refreshData } = useAppContext()
    return (
        <PermissionGuard code="documents.send" fallback={<AcessoNaoAutorizado />}>
            <UploadView onUploaded={refreshData} />
        </PermissionGuard>
    )
}

function ValidationRoute() {
    const { schemas, selectedDocument, selectedDocumentId, refreshData } = useAppContext()
    const navigate = useNavigate()
    return (
        <PermissionGuard code="documents.validate" fallback={<AcessoNaoAutorizado />}>
            <ValidationView
                schemas={schemas}
                selectedDocument={selectedDocument}
                selectedDocumentId={selectedDocumentId}
                onValidated={refreshData}
                onBackToInbox={() => navigate(navPath('inbox'))}
            />
        </PermissionGuard>
    )
}

function OperationsRoute() {
    return (
        <PermissionGuard code="operations.access" fallback={<AcessoNaoAutorizado />}>
            <OperationsView />
        </PermissionGuard>
    )
}

function SettingsRoute() {
    const { schemas, layouts, refreshData } = useAppContext()
    return (
        <PermissionGuard code="roles.manage" fallback={<AcessoNaoAutorizado />}>
            <SettingsView schemas={schemas} layouts={layouts} onChanged={refreshData} />
        </PermissionGuard>
    )
}

function UsersRoute() {
    return (
        <PermissionGuard code="users.manage" fallback={<AcessoNaoAutorizado />}>
            <GerenciarUsuarios />
        </PermissionGuard>
    )
}

function RolesRoute() {
    return (
        <PermissionGuard code="roles.manage" fallback={<AcessoNaoAutorizado />}>
            <GerenciarRoles />
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
                { path: 'dashboard', element: <DashboardRoute />, errorElement: <ErrorBoundary /> },
                { path: 'inbox', element: <InboxRoute />, errorElement: <ErrorBoundary /> },
                { path: 'upload', element: <UploadRoute />, errorElement: <ErrorBoundary /> },
                { path: 'validation', element: <ValidationRoute />, errorElement: <ErrorBoundary /> },
                { path: 'operations', element: <OperationsRoute />, errorElement: <ErrorBoundary /> },
                { path: 'settings', element: <SettingsRoute />, errorElement: <ErrorBoundary /> },
                { path: 'users', element: <UsersRoute />, errorElement: <ErrorBoundary /> },
                { path: 'roles', element: <RolesRoute />, errorElement: <ErrorBoundary /> },
                { path: 'tenants', element: <TenantsRoute />, errorElement: <ErrorBoundary /> },
                { path: '*', element: <Navigate to="/" replace /> },
            ],
        },
    ])
}

export const router = createAppRouter()
