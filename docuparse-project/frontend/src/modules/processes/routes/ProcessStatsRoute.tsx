import { AcessoNaoAutorizado, useAuth } from '../../auth'
import { Alert } from '../../../shared/components'
import { useProcessStatsQuery } from '../hooks/useProcessStatsQuery'
import { ProcessStatsView } from '../components/ProcessStatsView'

function ProcessStatsPage() {
    const { data, loading, error } = useProcessStatsQuery()

    return (
        <div className="mx-auto flex max-w-5xl flex-col gap-4">
            {error ? <Alert tone="error">{error}</Alert> : null}
            {loading && !data ? <Alert>Carregando estatísticas...</Alert> : null}
            {data ? <ProcessStatsView stats={data} /> : null}
        </div>
    )
}

export function ProcessStatsRoute() {
    const { hasPermission } = useAuth()
    // Mesma regra da Visão Geral: `inbox.view` OU `operations.access`.
    if (!hasPermission('inbox.view') && !hasPermission('operations.access')) {
        return <AcessoNaoAutorizado />
    }
    return <ProcessStatsPage />
}
