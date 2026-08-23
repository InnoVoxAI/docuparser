import { AcessoNaoAutorizado, PermissionGuard } from '../../auth'
import { ProcessesView } from '../components/ProcessesView'

export function ProcessesRoute() {
    return (
        <PermissionGuard code="operations.access" fallback={<AcessoNaoAutorizado />}>
            <ProcessesView />
        </PermissionGuard>
    )
}
