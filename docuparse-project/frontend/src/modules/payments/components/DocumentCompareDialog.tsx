import { useEffect, useState, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { useBodyScrollLock } from '../../../shared/hooks'
import { buildChecks } from '../compareChecks'
import { usePaymentDocuments } from '../hooks'
import type { PaymentDocument } from '../schemas/payments'
import { formatMoney } from '../utils'
import { ComparisonStrip } from './ComparisonStrip'
import { DocumentPane } from './DocumentPane'

interface Props {
    invoice: PaymentDocument | null
    boletos: PaymentDocument[]
    /** Boleto mostrado de início quando há mais de um. */
    initialBoletoId?: string
    /** Ações do analista (confirmar, rejeitar), para decidir sem sair do popup. */
    footer?: ReactNode
    onClose: () => void
}

/** Popup com a nota e os boletos lado a lado, como na validação, e a conferência no topo. */
export function DocumentCompareDialog({ invoice, boletos, initialBoletoId, footer, onClose }: Props) {
    useBodyScrollLock()
    const [boletoId, setBoletoId] = useState(initialBoletoId ?? boletos[0]?.id ?? '')
    const ids = [...(invoice ? [invoice.id] : []), ...boletos.map((b) => b.id)]
    const states = usePaymentDocuments(ids)
    const details = Object.fromEntries(ids.map((id) => [id, states[id]?.detail]))
    const boleto = boletos.find((b) => b.id === boletoId) ?? boletos[0] ?? null

    useEffect(() => {
        const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [onClose])

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-2"
            role="dialog"
            aria-modal="true"
            aria-label="Documentos do processo"
        >
            <div className="flex h-[96vh] w-full max-w-[1500px] flex-col rounded-lg bg-white shadow-xl">
                <header className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                    <h2 className="text-base font-semibold text-zinc-900">Documentos do processo</h2>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Fechar"
                        className="rounded-md p-1 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800"
                    >
                        <X size={20} aria-hidden="true" />
                    </button>
                </header>
                <ComparisonStrip checks={buildChecks(invoice, boletos, details)} />
                {boletos.length > 1 ? (
                    <div
                        role="tablist"
                        aria-label="Boletos"
                        className="flex flex-wrap gap-2 border-b border-zinc-200 px-4 py-2"
                    >
                        {boletos.map((item, index) => (
                            <button
                                key={item.id}
                                type="button"
                                role="tab"
                                aria-selected={item.id === boleto?.id}
                                onClick={() => setBoletoId(item.id)}
                                className={`rounded-md px-3 py-1 text-sm font-medium ${
                                    item.id === boleto?.id
                                        ? 'bg-zinc-900 text-white'
                                        : 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200'
                                }`}
                            >
                                Boleto {index + 1} · {formatMoney(item.amount)}
                            </button>
                        ))}
                    </div>
                ) : null}
                <div className={`grid min-h-0 flex-1 gap-3 p-3 ${invoice && boleto ? 'lg:grid-cols-2' : ''}`}>
                    {invoice ? <DocumentPane kind="Nota fiscal" doc={invoice} state={states[invoice.id]} /> : null}
                    {boleto ? <DocumentPane kind="Boleto" doc={boleto} state={states[boleto.id]} /> : null}
                </div>
                {footer ? (
                    <footer className="flex justify-end border-t border-zinc-200 px-4 py-3">{footer}</footer>
                ) : null}
            </div>
        </div>
    )
}
