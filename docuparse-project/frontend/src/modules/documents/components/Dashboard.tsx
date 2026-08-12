import { Alert, Metric, Pagination, SearchInput } from '../../../shared/components'
import { useDocumentCount } from '../hooks/useDocumentCount'
import { useDocumentsQuery } from '../hooks/useDocumentsQuery'
import type { Document } from '../types'
import { DocumentTable } from './DocumentTable'

export function Dashboard({
    refreshSignal,
    onSelectRejected,
}: {
    refreshSignal?: number
    onSelectRejected?: (doc: Document) => void
}) {
    const { page, setPage, search, setSearch, data, loading, error } = useDocumentsQuery(undefined, {
        autoRefresh: true,
        refreshSignal,
    })
    const { data: total = 0 } = useDocumentCount(undefined, { refreshSignal })
    const { data: approved = 0 } = useDocumentCount('APPROVED', { refreshSignal })
    const { data: failed = 0 } = useDocumentCount('REJECTED', { refreshSignal })
    const pending = Math.max(total - approved - failed, 0)

    function handleSelectDocument(id: string) {
        const doc = data.results.find((d) => d.id === id)
        if (doc && doc.status === 'REJECTED' && onSelectRejected) {
            onSelectRejected(doc)
        }
    }

    return (
        <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Metric label="Total" value={total} />
                <Metric label="Pendentes" value={pending} />
                <Metric label="Aprovados" value={approved} />
                <Metric label="Falhas" value={failed} />
            </div>
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                    <div className="text-sm font-semibold">Documentos</div>
                    <SearchInput value={search} onChange={setSearch} placeholder="Buscar por nome, status, tipo..." />
                </div>
                {error ? <Alert tone="error">{error}</Alert> : null}
                {loading ? <Alert>Carregando documentos...</Alert> : null}
                <DocumentTable documents={data.results} onSelectDocument={handleSelectDocument} />
                <Pagination
                    page={page}
                    totalPages={data.total_pages}
                    count={data.count}
                    pageSize={data.page_size}
                    onPageChange={setPage}
                />
            </section>
        </div>
    )
}
