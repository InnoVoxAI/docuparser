import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { ImportReviewView } from '../components/ImportReviewView'

export function ImportReviewRoute() {
    return (
        <PermissionGuard code="inbox.view" fallback={<AcessoNaoAutorizado />}>
            <ImportReviewView />
        </PermissionGuard>
    )
}
