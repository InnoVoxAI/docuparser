import { useNavigate, useOutletContext } from 'react-router'
import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { navPath, type AppOutletContext } from '../../../main'
import { InboxView } from '../components/InboxView'

export function InboxRoute() {
    const { refreshSignal, navigateToValidation } = useOutletContext<AppOutletContext>()
    const navigate = useNavigate()
    return (
        <PermissionGuard code="inbox.view" fallback={<AcessoNaoAutorizado />}>
            <InboxView
                refreshSignal={refreshSignal}
                onNavigateToValidation={navigateToValidation}
                onNavigateToUpload={() => navigate(navPath('upload'))}
            />
        </PermissionGuard>
    )
}
