import { Link } from 'react-router'
import { ArrowLeft } from 'lucide-react'
import { AcessoNaoAutorizado, useAuth } from '../../auth'
import { Alert } from '../../../shared/components'
import { useProcessStatsQuery } from '../hooks/useProcessStatsQuery'
import { ProcessStatsView } from '../components/ProcessStatsView'

function ProcessStatsPage() {
    const { data, loading, error } = useProcessStatsQuery()

    return (
        <div className="mx-auto flex max-w-5xl flex-col gap-4">
            <div>
                <Link
                    to="/"
                    className="inline-flex items-center gap-1 text-sm font-medium text-zinc-500 hover:text-zinc-900"
                >
                    <ArrowLeft size={14} aria-hidden="true" />
                    Processos
                </Link>
                <h1 className="mt-1 text-xl font-semibold text-zinc-900">Estatísticas</h1>
                <p className="mt-1 text-sm text-zinc-500">
                    Visão agregada de todos os processos: onde estão parados, erros e volume.
                </p>
            </div>

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
