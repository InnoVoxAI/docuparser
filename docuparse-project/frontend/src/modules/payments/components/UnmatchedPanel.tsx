import { useState } from 'react'
import { Link2 } from 'lucide-react'
import { useAuth } from '../../auth'
import { useManualMatch } from '../hooks'
import type { PaymentDocument } from '../schemas/payments'
import { CandidateList } from './CandidateList'
import { DocumentCompareDialog } from './DocumentCompareDialog'
import { SelectionBar } from './SelectionBar'

/** Documentos sem match: o operador escolhe a nota e os boletos e monta o agrupamento à mão. */
export function UnmatchedPanel({ onCreated }: { onCreated: () => void }) {
    const { hasPermission } = useAuth()
    const canDecide = hasPermission('documents.validate')
    const [invoice, setInvoice] = useState<PaymentDocument | null>(null)
    const [boletos, setBoletos] = useState<PaymentDocument[]>([])
    const { create, busy, error, reset } = useManualMatch()
    // O que o popup mostra: a seleção inteira, ou um documento só (botão "ver" da lista).
    const [viewing, setViewing] = useState<{ invoice: PaymentDocument | null; boletos: PaymentDocument[] } | null>(null)

    const toggleBoleto = (doc: PaymentDocument) =>
        setBoletos((current) =>
            current.some((b) => b.id === doc.id) ? current.filter((b) => b.id !== doc.id) : [...current, doc],
        )
    const clear = () => {
        setInvoice(null)
        setBoletos([])
        reset()
    }
    const submit = async () => {
        if (!invoice) return
        try {
            await create({ invoiceId: invoice.id, boletoIds: boletos.map((b) => b.id) })
            clear()
            onCreated()
        } catch {
            // O hook já expõe a mensagem em `error`.
        }
    }

    return (
        <div className="flex flex-col gap-4">
            <p className="text-sm text-zinc-500">
                Documentos que não fazem parte de nenhum agrupamento. Os que estão em um agrupamento aguardando revisão
                só voltam aqui se esse agrupamento for rejeitado.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
                <CandidateList
                    kind="invoice"
                    title="Notas fiscais"
                    selected={invoice ? [invoice] : []}
                    onToggle={setInvoice}
                    onView={(doc) => setViewing({ invoice: doc, boletos: [] })}
                />
                <CandidateList
                    kind="boleto"
                    title="Boletos"
                    selected={boletos}
                    onToggle={toggleBoleto}
                    onView={(doc) => setViewing({ invoice: null, boletos: [doc] })}
                />
            </div>
            {canDecide ? (
                <SelectionBar
                    invoice={invoice}
                    boletos={boletos}
                    busy={busy}
                    error={error}
                    onClear={clear}
                    onCreate={() => void submit()}
                    onCompare={() => setViewing({ invoice, boletos })}
                />
            ) : null}
            {viewing ? (
                <DocumentCompareDialog
                    invoice={viewing.invoice}
                    boletos={viewing.boletos}
                    onClose={() => setViewing(null)}
                    footer={
                        canDecide && viewing.invoice && viewing.boletos.length > 0 ? (
                            <button
                                type="button"
                                disabled={busy}
                                onClick={() => {
                                    setViewing(null)
                                    void submit()
                                }}
                                className="inline-flex h-9 items-center gap-1 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                            >
                                <Link2 size={16} aria-hidden="true" /> Montar agrupamento
                            </button>
                        ) : null
                    }
                />
            ) : null}
        </div>
    )
}
