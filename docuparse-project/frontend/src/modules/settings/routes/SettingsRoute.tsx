import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { SettingsView } from '../components/SettingsView'

export function SettingsRoute() {
    return (
        <PermissionGuard code="models.edit" fallback={<AcessoNaoAutorizado />}>
            <SettingsView />
        </PermissionGuard>
    )
}
