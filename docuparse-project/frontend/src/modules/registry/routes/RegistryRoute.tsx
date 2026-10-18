import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { RegistryView } from '../components/RegistryView'

export function RegistryRoute() {
    return (
        <PermissionGuard code="inbox.view" fallback={<AcessoNaoAutorizado />}>
            <RegistryView />
        </PermissionGuard>
    )
}
