import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { TenantsView } from '../components/TenantsView'

export function TenantsRoute() {
    return (
        <PermissionGuard code="tenants.manage" fallback={<AcessoNaoAutorizado />}>
            <TenantsView />
        </PermissionGuard>
    )
}
