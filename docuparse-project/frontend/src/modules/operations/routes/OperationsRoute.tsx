import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { OperationsView } from '../components/OperationsView'

export function OperationsRoute() {
    return (
        <PermissionGuard code="operations.access" fallback={<AcessoNaoAutorizado />}>
            <OperationsView />
        </PermissionGuard>
    )
}
