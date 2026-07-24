import { useState } from 'react'
import { Eye, RefreshCw, Trash2, X, XCircle } from 'lucide-react'
import { Alert, EmptyState, Pagination, SearchInput } from '../../../shared/components'
import { formatDate } from '../../../shared/utils'
import { useDocumentsQuery } from '../hooks/useDocumentsQuery'
import type { Document } from '../types'

function RejectedRow({
    document,
    onReprocess,
    onDelete,
}: {
    document: Document
    onReprocess: (id: string) => void
    onDelete: (id: string) => void
}) {
    const [viewingMotivo, setViewingMotivo] = useState(false)
    return (
        <tr className="hover:bg-zinc-50">
            <td className="px-4 py-3">
                <div className="font-medium">{document.original_filename || document.id}</div>
            </td>
            <td className="max-w-[300px] px-4 py-3 text-zinc-600">
                {viewingMotivo ? (
                    <div className="rounded-md border border-zinc-200 bg-zinc-50 p-2 text-xs whitespace-pre-wrap">
                        {document.rejection_notes || '—'}
                        <button
                            type="button"
                            onClick={() => setViewingMotivo(false)}
                            className="ml-2 text-zinc-400 hover:text-zinc-700"
                        >
                            <X size={12} aria-hidden="true" />
                        </button>
                    </div>
                ) : (
                    <span className="line-clamp-2">{document.rejection_notes ?? '—'}</span>
                )}
            </td>
            <td className="whitespace-nowrap px-4 py-3 text-zinc-500">
                {formatDate(document.decision_date ?? document.updated_at)}
            </td>
            <td className="px-4 py-3">
                <div className="flex flex-wrap gap-2">
                    <button
                        type="button"
                        onClick={() => setViewingMotivo((v) => !v)}
                        className="inline-flex items-center gap-1 rounded border border-zinc-300 bg-white px-2 py-1 text-xs font-medium hover:bg-zinc-100"
                    >
                        <Eye size={12} aria-hidden="true" />
                        Visualizar Motivo
                    </button>
                    <button
                        type="button"
                        onClick={() => onReprocess(document.id)}
                        className="inline-flex items-center gap-1 rounded border border-zinc-300 bg-white px-2 py-1 text-xs font-medium hover:bg-zinc-100"
                    >
                        <RefreshCw size={12} aria-hidden="true" />
                        Reprocessar
                    </button>
                    <button
                        type="button"
                        onClick={() => onDelete(document.id)}
                        className="inline-flex items-center gap-1 rounded border border-red-200 bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
                    >
                        <Trash2 size={12} aria-hidden="true" />
                        Excluir
                    </button>
                </div>
            </td>
        </tr>
    )
}

export function RejectedView({
    refreshSignal,
    onReprocess,
    onDelete,
    onRefresh,
}: {
    refreshSignal?: number
    onReprocess: (id: string) => void
    onDelete: (id: string) => void
    onRefresh: () => void
}) {
    const { page, setPage, search, setSearch, data, loading, error } = useDocumentsQuery('REJECTED', {
        refreshSignal,
    })
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                <div className="text-sm font-semibold">Documentos rejeitados</div>
                <div className="flex items-center gap-2">
                    <SearchInput value={search} onChange={setSearch} placeholder="Buscar por nome, motivo..." />
                    <button
                        type="button"
                        onClick={onRefresh}
                        className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
                    >
                        <RefreshCw size={16} aria-hidden="true" />
                        Atualizar
                    </button>
                </div>
            </div>
            {error ? <Alert tone="error">{error}</Alert> : null}
            {loading ? <Alert>Carregando documentos...</Alert> : null}
            {data.results.length === 0 ? (
                <EmptyState icon={XCircle} text="Nenhum documento rejeitado." />
            ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-zinc-200 text-sm">
                        <thead className="bg-zinc-50 text-left text-xs uppercase text-zinc-500">
                            <tr>
                                <th className="px-4 py-3">Documento</th>
                                <th className="px-4 py-3">Motivo da rejeicao</th>
                                <th className="px-4 py-3">Data</th>
                                <th className="px-4 py-3">Acoes</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-100">
                            {data.results.map((doc) => (
                                <RejectedRow
                                    key={doc.id}
                                    document={doc}
                                    onReprocess={onReprocess}
                                    onDelete={onDelete}
                                />
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
            <Pagination
                page={page}
                totalPages={data.total_pages}
                count={data.count}
                pageSize={data.page_size}
                onPageChange={setPage}
            />
        </section>
    )
}
