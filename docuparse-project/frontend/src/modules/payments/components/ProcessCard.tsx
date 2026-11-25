import { useState } from 'react'
import { Columns2 } from 'lucide-react'
import { formatDate } from '../../../shared/utils'
import type { Decision, PaymentProcess } from '../schemas/payments'
import { describeCoverage, formatMoney, ORIGIN_LABELS } from '../utils'
import { DocumentCompareDialog } from './DocumentCompareDialog'
import { DocumentLine } from './DocumentLine'
import { ProcessActions } from './ProcessActions'

interface Props {
    process: PaymentProcess
    canDecide: boolean
    busy: boolean
    onDecide: (process: PaymentProcess, decision: Decision) => void
    onUndo: (process: PaymentProcess) => void
}

/** Um agrupamento: a nota, os boletos e, se ainda pendente, as ações de aprovar ou rejeitar. */
export function ProcessCard({ process, canDecide, busy, onDecide, onUndo }: Props) {
    // `focus` é o boleto que o popup mostra de início; `null` fecha o popup.
    const [viewing, setViewing] = useState<{ focus?: string } | null>(null)
    const coverage = describeCoverage(process.invoice_amount, process.boletos_total)
    const close = () => setViewing(null)
    return (
        <article className="rounded-lg border border-zinc-200 bg-white" aria-label="Processo de pagamento">
            <header className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 px-4 py-2 text-xs text-zinc-500">
                <span>
                    {ORIGIN_LABELS[process.origin]} · {formatDate(process.created_at)}
                </span>
                <div className="flex items-center gap-3">
                    <button
                        type="button"
                        onClick={() => setViewing({})}
                        className="inline-flex items-center gap-1 rounded-md border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-100"
                    >
                        <Columns2 size={14} aria-hidden="true" /> Ver documentos
                    </button>
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
                </div>
            </header>
            <ul className="divide-y divide-zinc-100 px-4">
                <DocumentLine kind="Nota fiscal" doc={process.invoice} onOpen={() => setViewing({})} />
                {process.boletos.map((boleto) => (
                    <DocumentLine
                        key={boleto.id}
                        kind="Boleto"
                        doc={boleto}
                        onOpen={() => setViewing({ focus: boleto.id })}
                    />
                ))}
            </ul>
            <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-100 px-4 py-3">
                <p className="text-sm text-zinc-600">
                    Boletos somam <strong>{formatMoney(process.boletos_total)}</strong>. {coverage}
                </p>
                <ProcessActions
                    process={process}
                    canDecide={canDecide}
                    busy={busy}
                    onDecide={onDecide}
                    onUndo={onUndo}
                />
            </footer>
            {viewing ? (
                <DocumentCompareDialog
                    invoice={process.invoice}
                    boletos={process.boletos}
                    initialBoletoId={viewing.focus}
                    onClose={close}
                    footer={
                        <ProcessActions
                            process={process}
                            canDecide={canDecide}
                            busy={busy}
                            onDecide={(target, decision) => {
                                close()
                                onDecide(target, decision)
                            }}
                            onUndo={(target) => {
                                close()
                                onUndo(target)
                            }}
                        />
                    }
                />
            ) : null}
        </article>
    )
}
