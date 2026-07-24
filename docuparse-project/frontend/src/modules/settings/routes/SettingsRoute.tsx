import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { SettingsView } from '../components/SettingsView'

export function SettingsRoute() {
    return (
        <PermissionGuard code="roles.manage" fallback={<AcessoNaoAutorizado />}>
            <SettingsView />
        </PermissionGuard>
    )
}
