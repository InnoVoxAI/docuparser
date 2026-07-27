import { X } from 'lucide-react'
import { Alert } from '../../../shared/components'
import { parseFieldEntry } from '../utils'
import type { FieldVersionsResponse } from '../types'

const FIELD_VERSION_SOURCE_LABELS = {
    INITIAL_EXTRACTION: 'Extração inicial',
    PROCESSING: 'Processamento',
    REPROCESSING: 'Reprocessamento',
    MANUAL_EDIT: 'Edição manual',
}

export function FieldVersionHistoryModal({
    history,
    loading,
    error,
    onClose,
}: {
    history: FieldVersionsResponse | null
    loading: boolean
    error: string
    onClose: () => void
}) {
    const versions = history?.results ?? []
    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
            role="dialog"
            aria-modal="true"
        >
            <div className="flex max-h-[80vh] w-full max-w-2xl flex-col rounded-md border border-zinc-200 bg-white shadow-lg">
                <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                    <div className="text-sm font-semibold">Histórico de versões (somente leitura)</div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded p-1 text-zinc-500 hover:bg-zinc-100"
                        aria-label="Fechar"
                    >
                        <X size={16} aria-hidden="true" />
                    </button>
                </div>
                <div className="overflow-auto p-4">
                    {loading ? (
                        <div className="py-6 text-center text-sm text-zinc-500">Carregando histórico...</div>
                    ) : error ? (
                        <Alert tone="error">{error}</Alert>
                    ) : versions.length === 0 ? (
                        <div className="py-6 text-center text-sm text-zinc-400">
                            Nenhuma versão registrada para este documento.
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {versions.map((version) => (
                                <div key={version.version_number} className="rounded-md border border-zinc-200">
                                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 px-3 py-2">
                                        <div className="text-sm font-semibold">
                                            Versão {version.version_number}
                                            {version.is_active ? (
                                                <span className="ml-2 rounded bg-green-100 px-1.5 py-0.5 text-xs font-medium text-green-700">
                                                    Ativa
                                                </span>
                                            ) : null}
                                        </div>
                                        <div className="text-xs text-zinc-500">
                                            {FIELD_VERSION_SOURCE_LABELS[version.source_type] || version.source_type}
                                            {' · '}
                                            {version.created_at ? new Date(version.created_at).toLocaleString() : ''}
                                            {version.created_by ? ` · ${version.created_by}` : ''}
                                        </div>
                                    </div>
                                    <div className="divide-y divide-zinc-100">
                                        {Object.entries(version.fields || {}).map(([name, raw]) => {
                                            const { value, confidence } = parseFieldEntry(raw)
                                            return (
                                                <div
                                                    key={name}
                                                    className="grid grid-cols-[200px_1fr_auto] gap-2 px-3 py-2 text-sm"
                                                >
                                                    <div className="font-medium text-zinc-600">{name}</div>
                                                    <div className="break-words text-zinc-900">{value}</div>
                                                    <div className="text-xs text-zinc-400">
                                                        {confidence != null ? `${(confidence * 100).toFixed(0)}%` : '—'}
                                                    </div>
                                                </div>
                                            )
                                        })}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
