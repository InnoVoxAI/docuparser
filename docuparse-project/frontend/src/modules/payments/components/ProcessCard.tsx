import { Check, X } from 'lucide-react'
import { formatDate } from '../../../shared/utils'
import type { Decision, PaymentProcess } from '../schemas/payments'
import { describeCoverage, formatMoney, ORIGIN_LABELS } from '../utils'
import { DocumentLine } from './DocumentLine'

interface Props {
    process: PaymentProcess
    canDecide: boolean
    busy: boolean
    onDecide: (process: PaymentProcess, decision: Decision) => void
}

/** Um agrupamento: a nota, os boletos e, se ainda pendente, as ações de aprovar ou rejeitar. */
export function ProcessCard({ process, canDecide, busy, onDecide }: Props) {
    const coverage = describeCoverage(process.invoice_amount, process.boletos_total)
    return (
        <article className="rounded-lg border border-zinc-200 bg-white" aria-label="Processo de pagamento">
            <header className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 px-4 py-2 text-xs text-zinc-500">
                <span>
                    {ORIGIN_LABELS[process.origin]} · {formatDate(process.created_at)}
                </span>
                {process.decided_by ? (
                    <span>
                        {process.status === 'CONFIRMED' ? 'Confirmado' : 'Rejeitado'} por {process.decided_by} em{' '}
                        {formatDate(process.decided_at)}
                    </span>
                ) : (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 font-semibold text-amber-800">
                        Aguardando confirmação
                    </span>
                )}
            </header>
            <ul className="divide-y divide-zinc-100 px-4">
                <DocumentLine kind="Nota fiscal" doc={process.invoice} />
                {process.boletos.map((boleto) => (
                    <DocumentLine key={boleto.id} kind="Boleto" doc={boleto} />
                ))}
            </ul>
            <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-100 px-4 py-3">
                <p className="text-sm text-zinc-600">
                    Boletos somam <strong>{formatMoney(process.boletos_total)}</strong>. {coverage}
                </p>
                {process.status === 'PENDING' && canDecide ? (
                    <div className="flex gap-2">
                        <button
                            type="button"
                            disabled={busy}
                            onClick={() => onDecide(process, 'reject')}
                            className="inline-flex h-9 items-center gap-1 rounded-md border border-zinc-300 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50"
                        >
                            <X size={16} aria-hidden="true" /> Rejeitar
                        </button>
                        <button
                            type="button"
                            disabled={busy}
                            onClick={() => onDecide(process, 'confirm')}
                            className="inline-flex h-9 items-center gap-1 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                        >
                            <Check size={16} aria-hidden="true" /> Confirmar
                        </button>
                    </div>
                ) : null}
            </footer>
        </article>
    )
}
