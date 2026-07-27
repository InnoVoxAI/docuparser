import { FileText, RefreshCw } from 'lucide-react'
import { EmptyState, KeyValueGrid } from '../../../shared/components'
import type { DlqEvent } from '../types'

export function DlqEventDetail({
    stream,
    event,
    requeueing,
    onSimulate,
    onRequeue,
}: {
    stream: string
    event: DlqEvent | null
    requeueing: boolean
    onSimulate: () => void
    onRequeue: () => void
}) {
    return (
        <div className="rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">Detalhe</div>
            {event ? (
                <div className="space-y-3 p-4">
                    <KeyValueGrid
                        values={{
                            stream: event.original_stream || stream,
                            origem: event.source || '-',
                            erro: event.error_type || '-',
                        }}
                    />
                    <div className="flex flex-wrap gap-2">
                        <button
                            type="button"
                            onClick={onSimulate}
                            disabled={requeueing}
                            className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <RefreshCw size={16} aria-hidden="true" />
                            Simular
                        </button>
                        <button
                            type="button"
                            onClick={onRequeue}
                            disabled={requeueing}
                            className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <RefreshCw size={16} aria-hidden="true" />
                            Reenfileirar
                        </button>
                    </div>
                    <div>
                        <div className="mb-1 text-xs font-semibold uppercase text-zinc-500">Mensagem</div>
                        <div className="rounded-md border border-red-100 bg-red-50 p-3 text-sm text-red-800">
                            {event.error || '-'}
                        </div>
                    </div>
                    <div>
                        <div className="mb-1 text-xs font-semibold uppercase text-zinc-500">Payload original</div>
                        <pre className="max-h-[420px] overflow-auto rounded-md bg-zinc-950 p-3 text-xs text-zinc-50">
                            {JSON.stringify(event.payload || {}, null, 2)}
                        </pre>
                    </div>
                </div>
            ) : (
                <EmptyState icon={FileText} text="Selecione um evento para inspecionar." />
            )}
        </div>
    )
}
