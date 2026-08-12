import { useOutletContext } from 'react-router'
import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import type { AppOutletContext } from '../../../types'
import { Dashboard } from '../components/Dashboard'

export function DashboardRoute() {
    const { refreshSignal, onSelectRejected } = useOutletContext<AppOutletContext>()
    return (
        <PermissionGuard code="inbox.view" fallback={<AcessoNaoAutorizado />}>
            <Dashboard refreshSignal={refreshSignal} onSelectRejected={onSelectRejected} />
        </PermissionGuard>
    )
}
