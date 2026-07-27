import { useOutletContext } from 'react-router'
import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import type { AppOutletContext } from '../../../types'
import { UploadView } from '../components/UploadView'

export function UploadRoute() {
    const { refreshData } = useOutletContext<AppOutletContext>()
    return (
        <PermissionGuard code="documents.send" fallback={<AcessoNaoAutorizado />}>
            <UploadView onUploaded={refreshData} />
        </PermissionGuard>
    )
}
