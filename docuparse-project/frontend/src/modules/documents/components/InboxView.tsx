import { Upload } from 'lucide-react'
import { Alert, Pagination, SearchInput } from '../../../shared/components'
import { useDocumentsQuery } from '../hooks/useDocumentsQuery'
import { DocumentTable } from './DocumentTable'

const INBOX_STATUS_BUCKET = 'RECEIVED,OCR_COMPLETED,EXTRACTION_COMPLETED,VALIDATION_PENDING'

export function InboxView({
    refreshSignal,
    onNavigateToValidation,
    onNavigateToUpload,
}: {
    refreshSignal?: number
    onNavigateToValidation: (id: string) => void
    onNavigateToUpload: () => void
}) {
    const { page, setPage, search, setSearch, data, loading, error } = useDocumentsQuery(INBOX_STATUS_BUCKET, {
        autoRefresh: true,
        refreshSignal,
    })
    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <button
                    type="button"
                    onClick={onNavigateToUpload}
                    className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-medium text-white hover:bg-zinc-700"
                >
                    <Upload size={16} aria-hidden="true" />
                    Enviar Documento
                </button>
            </div>
            <section className="rounded-md border border-zinc-200 bg-white">
                <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                    <div className="text-sm font-semibold">Documentos pendentes</div>
                    <SearchInput value={search} onChange={setSearch} placeholder="Buscar por nome, tipo..." />
                </div>
                {error ? <Alert tone="error">{error}</Alert> : null}
                {loading ? <Alert>Carregando documentos...</Alert> : null}
                <DocumentTable documents={data.results} onSelectDocument={onNavigateToValidation} />
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
