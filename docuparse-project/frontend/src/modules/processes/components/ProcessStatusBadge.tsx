import { STATUS_GROUP_LABELS } from '../types'

// Cores por rótulo "de negócio". Chave = texto exato de STATUS_GROUP_LABELS
// (o backend já manda `status_label` pronto).
const TONE_BY_LABEL: Record<string, string> = {
    [STATUS_GROUP_LABELS.erro]: 'bg-red-50 text-red-700 ring-red-200',
    [STATUS_GROUP_LABELS.aguardando_validacao]: 'bg-amber-50 text-amber-700 ring-amber-200',
    [STATUS_GROUP_LABELS.aguardando_classificacao]: 'bg-sky-50 text-sky-700 ring-sky-200',
    [STATUS_GROUP_LABELS.em_fila]: 'bg-zinc-100 text-zinc-600 ring-zinc-200',
}

export function ProcessStatusBadge({ label }: { label: string }) {
    const tone = TONE_BY_LABEL[label] ?? 'bg-zinc-100 text-zinc-600 ring-zinc-200'
    return <span className={`inline-flex rounded px-2 py-1 text-xs font-medium ring-1 ${tone}`}>{label || '-'}</span>
}
