import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { PaymentsView } from '../components/PaymentsView'

export function PaymentsRoute() {
    return (
        <PermissionGuard code="inbox.view" fallback={<AcessoNaoAutorizado />}>
            <PaymentsView />
        </PermissionGuard>
    )
}
