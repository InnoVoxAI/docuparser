import { STATUS_GROUP_LABELS } from '../types'

// Cores por rótulo "de negócio". Chave = texto exato de STATUS_GROUP_LABELS
// (o backend já manda `status_label` pronto). `dot` é a cor sólida do círculo
// indicador; `pill` é o fundo/anel claro do badge — mesma paleta, dois tons.
const TONE_BY_LABEL: Record<string, { dot: string; pill: string }> = {
    [STATUS_GROUP_LABELS.erro]: { dot: 'bg-red-500', pill: 'bg-red-50 text-red-700 ring-red-200' },
    [STATUS_GROUP_LABELS.aguardando_validacao]: {
        dot: 'bg-amber-500',
        pill: 'bg-amber-50 text-amber-700 ring-amber-200',
    },
    [STATUS_GROUP_LABELS.aguardando_classificacao]: {
        dot: 'bg-sky-500',
        pill: 'bg-sky-50 text-sky-700 ring-sky-200',
    },
    [STATUS_GROUP_LABELS.em_fila]: { dot: 'bg-zinc-400', pill: 'bg-zinc-100 text-zinc-600 ring-zinc-200' },
}
const DEFAULT_TONE = { dot: 'bg-zinc-400', pill: 'bg-zinc-100 text-zinc-600 ring-zinc-200' }

/** Badge de status "de negócio" — um círculo colorido junto ao texto pra
 * diferenciar os status de relance, sem precisar ler a etiqueta inteira. */
export function ProcessStatusBadge({ label }: { label: string }) {
    const tone = TONE_BY_LABEL[label] ?? DEFAULT_TONE
    return (
        <span className={`inline-flex items-center gap-1.5 rounded px-2 py-1 text-xs font-medium ring-1 ${tone.pill}`}>
            <span aria-hidden="true" className={`h-2 w-2 shrink-0 rounded-full ${tone.dot}`} />
            {label || '-'}
        </span>
    )
}
