import { useState } from 'react'
import { CheckCircle2, FileJson } from 'lucide-react'
import { Alert, EmptyState, Pagination, SearchInput, StatusBadge } from '../../../shared/components'
import { formatDate } from '../../../shared/utils'
import { useDocumentsQuery } from '../hooks/useDocumentsQuery'
import type { Document } from '../types'
import { ExtractedFieldsModal } from './ExtractedFieldsModal'

export function ApprovedView({ refreshSignal }: { refreshSignal?: number }) {
    const { page, setPage, search, setSearch, data, loading, error } = useDocumentsQuery('APPROVED', {
        refreshSignal,
    })
    const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                <div className="text-sm font-semibold">Documentos aprovados</div>
                <SearchInput value={search} onChange={setSearch} placeholder="Buscar por nome, tipo..." />
            </div>
            {error ? <Alert tone="error">{error}</Alert> : null}
            {loading ? <Alert>Carregando documentos...</Alert> : null}
            {data.results.length === 0 ? (
                <EmptyState icon={CheckCircle2} text="Nenhum documento aprovado." />
            ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-zinc-200 text-sm">
                        <thead className="bg-zinc-50 text-left text-xs uppercase text-zinc-500">
                            <tr>
                                <th className="px-4 py-3">Documento</th>
                                <th className="px-4 py-3">Status</th>
                                <th className="px-4 py-3">Data de aprovação</th>
                                <th className="px-4 py-3">Campos extraídos</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-100">
                            {data.results.map((doc) => (
                                <tr key={doc.id} className="hover:bg-zinc-50">
                                    <td className="px-4 py-3 font-medium">{doc.original_filename || doc.id}</td>
                                    <td className="px-4 py-3">
                                        <StatusBadge status={doc.status} />
                                    </td>
                                    <td className="whitespace-nowrap px-4 py-3 text-zinc-500">
                                        {formatDate(doc.approved_at ?? doc.decision_date ?? doc.updated_at)}
                                    </td>
                                    <td className="px-4 py-3">
                                        {doc.extraction_result?.fields &&
                                        Object.keys(doc.extraction_result.fields).length > 0 ? (
                                            <button
                                                type="button"
                                                onClick={() => setSelectedDoc(doc)}
                                                className="inline-flex items-center gap-1.5 rounded-md border border-zinc-300 bg-white px-2.5 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
                                            >
                                                <FileJson size={14} aria-hidden="true" />
                                                Ver campos
                                            </button>
                                        ) : (
                                            <span className="text-xs text-zinc-400">—</span>
                                        )}
                                    </td>
                                </tr>
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
            {selectedDoc && <ExtractedFieldsModal doc={selectedDoc} onClose={() => setSelectedDoc(null)} />}
        </section>
    )
}
