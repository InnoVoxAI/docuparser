import { RefreshCw } from 'lucide-react'
import { Metric } from '../../../shared/components'
import type { DlqSummary } from '../types'

export function DlqStreamSummary({
    summary,
    selectedStream,
    onSelectStream,
    onRefresh,
}: {
    summary: DlqSummary
    selectedStream: string
    onSelectStream: (stream: string) => void
    onRefresh: () => void
}) {
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 px-4 py-3">
                <div>
                    <div className="text-sm font-semibold">Dead-letter queues</div>
                    <div className="mt-1 text-xs text-zinc-500">
                        Eventos que falharam nos workers e aguardam revisao operacional.
                    </div>
                </div>
                <button
                    type="button"
                    onClick={onRefresh}
                    className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                >
                    <RefreshCw size={16} aria-hidden="true" />
                    Atualizar
                </button>
            </div>
            <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-4">
                <Metric label="Total em DLQ" value={summary.total || 0} />
                {(summary.streams || []).map((item) => (
                    <button
                        key={item.stream}
                        type="button"
                        onClick={() => onSelectStream(item.stream)}
                        className={`rounded-md border p-3 text-left ${selectedStream === item.stream ? 'border-zinc-900 bg-zinc-50' : 'border-zinc-200 bg-white hover:bg-zinc-50'}`}
                    >
                        <div className="truncate text-xs font-semibold uppercase text-zinc-500">{item.stream}</div>
                        <div className="mt-2 text-2xl font-semibold">{item.count}</div>
                        <div className="mt-1 truncate text-xs text-zinc-500">
                            {item.latest?.error_type || 'Sem eventos'}
                        </div>
                    </button>
                ))}
            </div>
        </section>
    )
}
