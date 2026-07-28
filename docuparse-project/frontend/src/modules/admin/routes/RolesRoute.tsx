import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { GerenciarRoles } from '../components/GerenciarRoles'

export function RolesRoute() {
    return (
        <PermissionGuard code="roles.manage" fallback={<AcessoNaoAutorizado />}>
            <GerenciarRoles />
        </PermissionGuard>
    )
}
