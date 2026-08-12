import { RefreshCw, Trash2, X } from 'lucide-react'
import { formatDate } from '../../../shared/utils'
import type { Document } from '../types'

export function RejectedDocumentModal({
    doc,
    onClose,
    onReprocess,
    onDelete,
}: {
    doc: Document
    onClose: () => void
    onReprocess: (id: string) => void
    onDelete: (id: string) => void
}) {
    return (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-lg">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold">Documento Rejeitado</h3>
                    <button type="button" onClick={onClose} className="text-zinc-400 hover:text-zinc-700">
                        <X size={20} aria-hidden="true" />
                    </button>
                </div>
                <div className="space-y-3 text-sm">
                    <div>
                        <div className="text-xs font-semibold uppercase text-zinc-500 mb-1">Arquivo</div>
                        <div className="font-medium">{doc.original_filename || doc.id}</div>
                    </div>
                    <div>
                        <div className="text-xs font-semibold uppercase text-zinc-500 mb-1">Motivo da rejeição</div>
                        <div className="rounded-md border border-zinc-200 bg-zinc-50 p-2 text-zinc-700 whitespace-pre-wrap">
                            {doc.rejection_notes || 'Motivo não informado'}
                        </div>
                    </div>
                    <div>
                        <div className="text-xs font-semibold uppercase text-zinc-500 mb-1">Data da rejeição</div>
                        <div className="text-zinc-500">{formatDate(doc.rejected_at ?? doc.decision_date)}</div>
                    </div>
                </div>
                <div className="flex gap-2 justify-end mt-5">
                    <button
                        type="button"
                        onClick={() => {
                            onDelete(doc.id)
                            onClose()
                        }}
                        className="inline-flex items-center gap-1 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100"
                    >
                        <Trash2 size={14} aria-hidden="true" />
                        Excluir
                    </button>
                    <button
                        type="button"
                        onClick={() => {
                            onReprocess(doc.id)
                            onClose()
                        }}
                        className="inline-flex items-center gap-1 rounded bg-zinc-900 px-3 py-2 text-sm font-medium text-white hover:bg-zinc-700"
                    >
                        <RefreshCw size={14} aria-hidden="true" />
                        Reprocessar
                    </button>
                </div>
            </div>
        </div>
    )
}
