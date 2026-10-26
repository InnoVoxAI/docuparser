import { formatDate } from '../../../shared/utils'
import type { ImportOverview } from '../schemas/registry'
import { summarizePending } from '../utils'

/** Onde estamos: quando foi a última sincronização e o que está pendente, por ação. */
export function ReviewSummary({ overview }: { overview: ImportOverview | undefined }) {
    if (!overview) return null
    const batch = overview.latest_batch
    const pending = summarizePending(overview.pending_by_action)
    return (
        <p className="text-sm text-zinc-600">
            {batch
                ? `Última sincronização: ${formatDate(batch.finished_at ?? batch.created_at)}${batch.started_by ? ` por ${batch.started_by}` : ''}. `
                : 'Nenhuma sincronização ainda. '}
            {pending ? (
                <>
                    Pendente: <strong className="text-zinc-900">{pending}</strong>.
                </>
            ) : (
                'Nada pendente.'
            )}
        </p>
    )
}
