import { Link } from 'react-router'
import { RefreshCw } from 'lucide-react'
import { Alert } from '../../../shared/components'
import { navPath, readError } from '../../../shared/utils'
import { useAuth } from '../../auth'
import { useImportOverview, useStartSync } from '../hooks'

/** Botão de sincronizar com o Superlógica, andamento do último lote e atalho para a confirmação. */
export function SyncPanel() {
    const { hasPermission } = useAuth()
    const overview = useImportOverview()
    const sync = useStartSync()

    const canEdit = hasPermission('models.edit')
    const data = overview.data
    const batch = data?.latest_batch ?? null
    const running = batch?.status === 'running' || sync.isPending
    const pending = data ? Object.values(data.pending_by_action).reduce((total, n) => total + n, 0) : 0

    // Sem credenciais não há nada a chamar: o botão explica o motivo.
    const blocked = !canEdit
        ? 'Você não tem permissão para sincronizar.'
        : data && !data.credentials_configured
          ? 'Configure as credenciais do Superlógica em Configurações > Integrações.'
          : ''

    return (
        <div className="flex flex-wrap items-center gap-3">
            <button
                type="button"
                onClick={() => sync.mutate()}
                disabled={running || Boolean(blocked) || overview.isLoading}
                className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
            >
                <RefreshCw size={16} aria-hidden="true" className={running ? 'animate-spin' : ''} />
                {running ? 'Sincronizando...' : 'Sincronizar com Superlógica'}
            </button>
            {blocked ? <span className="text-xs text-zinc-500">{blocked}</span> : null}
            {pending > 0 ? (
                <Link to={navPath('registry-import')} className="text-sm font-medium text-zinc-900 underline">
                    Revisar {pending} {pending === 1 ? 'proposta' : 'propostas'}
                </Link>
            ) : batch?.status === 'ready' && !running ? (
                <span className="text-xs text-zinc-500">Nada novo para confirmar.</span>
            ) : null}
            {sync.error ? (
                <div className="basis-full">
                    <Alert tone="error">{readError(sync.error, 'Nao foi possivel iniciar a sincronizacao.')}</Alert>
                </div>
            ) : null}
            {batch?.status === 'error' && !running ? (
                <div className="basis-full">
                    <Alert tone="error">A última sincronização falhou: {batch.error_message}</Alert>
                </div>
            ) : null}
        </div>
    )
}
