import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { GerenciarUsuarios } from '../components/GerenciarUsuarios'

export function UsersRoute() {
    return (
        <PermissionGuard code="users.manage" fallback={<AcessoNaoAutorizado />}>
            <GerenciarUsuarios />
        </PermissionGuard>
    )
}
