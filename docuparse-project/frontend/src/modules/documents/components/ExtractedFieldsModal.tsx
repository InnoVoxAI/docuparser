import { X } from 'lucide-react'
import type { Document } from '../types'

export function ExtractedFieldsModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
    const fields = doc.extraction_result?.fields || {}
    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
            onClick={(e) => {
                if (e.target === e.currentTarget) onClose()
            }}
            onKeyDown={(e) => {
                if (e.key === 'Escape') onClose()
            }}
            role="button"
            tabIndex={0}
            aria-label="Fechar modal"
        >
            <div className="flex max-h-[80vh] w-full max-w-2xl flex-col rounded-xl bg-white p-6 shadow-lg">
                <div className="mb-4 flex flex-shrink-0 items-center justify-between">
                    <div>
                        <h3 className="text-base font-semibold">Campos extraídos</h3>
                        <div className="mt-0.5 text-xs text-zinc-500">{doc.original_filename || doc.id}</div>
                    </div>
                    <button type="button" onClick={onClose} className="text-zinc-400 hover:text-zinc-700">
                        <X size={20} aria-hidden="true" />
                    </button>
                </div>
                <pre className="flex-1 overflow-auto rounded-md bg-zinc-950 p-4 text-xs text-zinc-50">
                    {JSON.stringify(fields, null, 2)}
                </pre>
            </div>
        </div>
    )
}
