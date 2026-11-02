import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { RulesView } from '../components/RulesView'

export function RulesRoute() {
    return (
        <PermissionGuard code="inbox.view" fallback={<AcessoNaoAutorizado />}>
            <RulesView />
        </PermissionGuard>
    )
}
