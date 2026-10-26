import { useState } from 'react'
import { Plus } from 'lucide-react'
import { Alert } from '../../../shared/components'
import { readError } from '../../../shared/utils'
import { useAuth } from '../../auth'
import { useCharts, useCondominiums, useImportOverview } from '../hooks'
import { ChartsPanel } from './ChartsPanel'
import { CondominiumsTable } from './CondominiumsTable'
import { CreateCondominiumDialog } from './CreateCondominiumDialog'
import { FirstSteps } from './FirstSteps'
import { SyncPanel } from './SyncPanel'

/** Cadastros: condomínios e planos de contas, com sincronização e cadastro manual. */
export function RegistryView() {
    const { hasPermission } = useAuth()
    const [creating, setCreating] = useState(false)
    const condominiums = useCondominiums()
    const charts = useCharts()
    const overview = useImportOverview()

    const error = condominiums.error ?? charts.error
    const loading = condominiums.isLoading || charts.isLoading

    return (
        <div className="space-y-4 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <SyncPanel />
                {hasPermission('models.edit') ? (
                    <button
                        type="button"
                        onClick={() => setCreating(true)}
                        className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                    >
                        <Plus size={16} aria-hidden="true" />
                        Novo condomínio
                    </button>
                ) : null}
            </div>
            {error ? <Alert tone="error">{readError(error, 'Nao foi possivel carregar os cadastros.')}</Alert> : null}
            {loading ? <p className="text-sm text-zinc-500">Carregando cadastros...</p> : null}
            {condominiums.data?.length === 0 && charts.data?.length === 0 ? (
                <FirstSteps credentialsConfigured={overview.data?.credentials_configured} />
            ) : null}
            {condominiums.data && charts.data ? (
                <>
                    <CondominiumsTable condominiums={condominiums.data} charts={charts.data} />
                    <ChartsPanel charts={charts.data} condominiums={condominiums.data} />
                </>
            ) : null}
            {creating ? (
                <CreateCondominiumDialog charts={charts.data ?? []} onClose={() => setCreating(false)} />
            ) : null}
        </div>
    )
}
