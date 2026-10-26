import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { RefreshCw } from 'lucide-react'
import { Alert } from '../../../shared/components'
import { formatDate, navPath, readError } from '../../../shared/utils'
import { useAuth } from '../../auth'
import { useImportOverview, useStartSync } from '../hooks'
import { pendingTotal, summarizePending } from '../utils'

/**
 * Botão de sincronizar com o Superlógica. Quando o lote que ESTA tela iniciou termina com
 * propostas, leva direto à confirmação; sem propostas, avisa que não há nada novo.
 */
export function SyncPanel() {
    const { hasPermission } = useAuth()
    const navigate = useNavigate()
    const overview = useImportOverview()
    const sync = useStartSync()
    const [startedBatchId, setStartedBatchId] = useState<string | null>(null)

    const canEdit = hasPermission('models.edit')
    const data = overview.data
    const batch = data?.latest_batch ?? null
    const running = batch?.status === 'running' || sync.isPending
    const pending = pendingTotal(data)
    const finishedNow = startedBatchId !== null && batch?.id === startedBatchId && batch.status === 'ready'

    useEffect(() => {
        if (finishedNow && pending > 0) {
            setStartedBatchId(null)
            navigate(navPath('registry-import'), { state: { fromSync: true } })
        }
    }, [finishedNow, pending, navigate])

    // Sem credenciais não há nada a chamar: o botão explica o motivo.
    const blocked = !canEdit
        ? 'Você não tem permissão para sincronizar.'
        : data && !data.credentials_configured && !overview.isFetching
          ? 'Configure as credenciais do Superlógica em Integrações (menu no canto superior direito).'
          : ''

    return (
        <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3">
                <button
                    type="button"
                    onClick={() => sync.mutate(undefined, { onSuccess: (started) => setStartedBatchId(started.id) })}
                    disabled={
                        running ||
                        Boolean(blocked) ||
                        overview.isLoading ||
                        (overview.isFetching && !data?.credentials_configured)
                    }
                    className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                >
                    <RefreshCw size={16} aria-hidden="true" className={running ? 'animate-spin' : ''} />
                    {running ? 'Sincronizando...' : 'Sincronizar com Superlógica'}
                </button>
                {blocked ? <span className="text-xs text-zinc-500">{blocked}</span> : null}
                {running ? (
                    <span className="text-xs text-zinc-500">
                        Lendo o cadastro do Superlógica. Leva alguns segundos.
                    </span>
                ) : pending > 0 ? (
                    <Link to={navPath('registry-import')} className="text-sm font-medium text-zinc-900 underline">
                        Revisar {pending} {pending === 1 ? 'proposta' : 'propostas'}
                    </Link>
                ) : batch?.status === 'ready' ? (
                    <span className="text-xs text-zinc-500">Nada novo para confirmar.</span>
                ) : null}
            </div>
            {batch && !running ? (
                <p className="text-xs text-zinc-500">
                    Última sincronização: {formatDate(batch.finished_at ?? batch.created_at)}
                    {batch.started_by ? ` por ${batch.started_by}` : ''}
                    {pending > 0 && data ? ` · pendente: ${summarizePending(data.pending_by_action)}` : ''}
                </p>
            ) : null}
            {sync.error ? (
                <Alert tone="error" className="">
                    {readError(sync.error, 'Nao foi possivel iniciar a sincronizacao.')}
                </Alert>
            ) : null}
            {batch?.status === 'error' && !running ? (
                <Alert tone="error" className="">
                    A última sincronização falhou: {batch.error_message}
                </Alert>
            ) : null}
        </div>
    )
}
