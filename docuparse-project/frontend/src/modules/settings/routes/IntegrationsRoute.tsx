import { PermissionGuard, AcessoNaoAutorizado } from '../../auth'
import { IntegrationSettingsPanel } from '../components/IntegrationSettingsPanel'

/** Integrações vivem fora de Configurações: página própria no layout novo, acessada pelo menu flutuante. */
export function IntegrationsRoute() {
    return (
        <PermissionGuard code="models.edit" fallback={<AcessoNaoAutorizado />}>
            <IntegrationSettingsPanel />
        </PermissionGuard>
    )
}
