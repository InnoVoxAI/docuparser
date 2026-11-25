import { Columns2, Link2, Undo2 } from 'lucide-react'
import { Alert } from '../../../shared/components'
import type { PaymentDocument } from '../schemas/payments'
import { formatMoney, selectionWarnings } from '../utils'

interface Props {
    invoice: PaymentDocument | null
    boletos: PaymentDocument[]
    busy: boolean
    error: string
    onClear: () => void
    onCreate: () => void
    /** Abre a nota e os boletos escolhidos lado a lado, antes de montar o agrupamento. */
    onCompare: () => void
}

/** O par escolhido, o que conferir nele e as ações de desfazer ou montar o agrupamento. */
export function SelectionBar({ invoice, boletos, busy, error, onClear, onCreate, onCompare }: Props) {
    const warnings = selectionWarnings(invoice, boletos)
    const total = boletos.reduce((sum, b) => sum + Number(b.amount ?? 0), 0)
    const empty = !invoice && boletos.length === 0
    return (
        <div aria-label="Seleção" className="sticky bottom-3 rounded-lg border border-zinc-300 bg-white p-3 shadow-lg">
            {error ? <Alert tone="error">{error}</Alert> : null}
            {warnings.map((warning) => (
                <p key={warning} className="mb-1 text-sm text-amber-800">
                    {warning}
                </p>
            ))}
            <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-zinc-700">
                    {empty ? (
                        'Escolha uma nota fiscal e um ou mais boletos.'
                    ) : (
                        <>
                            Nota: <strong>{invoice ? formatMoney(invoice.amount) : 'não escolhida'}</strong> · Boletos:{' '}
                            <strong>{boletos.length}</strong> ({formatMoney(total.toFixed(2))})
                        </>
                    )}
                </p>
                <div className="flex gap-2">
                    <button
                        type="button"
                        disabled={empty || busy}
                        onClick={onClear}
                        className="inline-flex h-9 items-center gap-1 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50"
                    >
                        <Undo2 size={16} aria-hidden="true" /> Desfazer seleção
                    </button>
                    <button
                        type="button"
                        disabled={!invoice || boletos.length === 0}
                        onClick={onCompare}
                        className="inline-flex h-9 items-center gap-1 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50"
                    >
                        <Columns2 size={16} aria-hidden="true" /> Comparar lado a lado
                    </button>
                    <button
                        type="button"
                        disabled={!invoice || boletos.length === 0 || busy}
                        onClick={onCreate}
                        className="inline-flex h-9 items-center gap-1 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                    >
                        <Link2 size={16} aria-hidden="true" /> Montar agrupamento
                    </button>
                </div>
            </div>
        </div>
    )
}
