import { useRef, useState, type ChangeEvent } from 'react'
import { Plus, Workflow } from 'lucide-react'
import { Alert, EmptyState, Pagination, SearchInput } from '../../../shared/components'
import { uploadManualDocument } from '../../../shared/lib/upload'
import { readError } from '../../../shared/utils'
import { useProcessesQuery } from '../hooks/useProcessesQuery'
import { ProcessFilters } from './ProcessFilters'
import { ProcessTable } from './ProcessTable'

/** Página inicial do app: tabela de processos, busca e filtro por status e
 * acesso ao envio de um novo documento. Sem cabeçalho/sidebar — só o conteúdo. */
export function ProcessOverviewView() {
    const { data, loading, error, statusGroup, setStatusGroup, search, setSearch, sort, toggleSort, goToPage, refresh } =
        useProcessesQuery()
    const fileInputRef = useRef<HTMLInputElement>(null)
    const [uploading, setUploading] = useState(false)
    const [uploadError, setUploadError] = useState('')

    const handleFileSelected = async (event: ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        // Reseta o input pra permitir selecionar o mesmo arquivo de novo em seguida.
        event.target.value = ''
        if (!file) return

        setUploading(true)
        setUploadError('')
        try {
            await uploadManualDocument(file)
            await refresh()
        } catch (requestError) {
            setUploadError(readError(requestError, 'Falha no upload.'))
        } finally {
            setUploading(false)
        }
    }

    return (
        <div className="mx-auto flex min-h-0 w-full max-w-5xl flex-1 flex-col gap-4">
            <div className="flex flex-wrap items-end justify-between gap-3 shrink-0">
                <div className="flex flex-wrap items-end gap-3">
                    <ProcessFilters selected={statusGroup} onChange={setStatusGroup} />
                    <SearchInput value={search} onChange={setSearch} placeholder="Buscar por nome do arquivo..." />
                </div>
                <div>
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.webp"
                        onChange={handleFileSelected}
                        className="hidden"
                    />
                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                        className="primary-button"
                    >
                        <Plus size={16} aria-hidden="true" />
                        {uploading ? 'Enviando...' : 'Novo processo'}
                    </button>
                </div>
            </div>

            {uploadError ? <Alert tone="error">{uploadError}</Alert> : null}
            {error ? <Alert tone="error">{error}</Alert> : null}

            {loading && data.results.length === 0 ? (
                <Alert>Carregando processos...</Alert>
            ) : data.results.length === 0 ? (
                <div className="rounded-lg border border-zinc-200 bg-white">
                    <EmptyState icon={Workflow} text="Nenhum processo encontrado para o filtro selecionado." />
                </div>
            ) : (
                <div className="flex min-h-0 flex-1 flex-col gap-3">
                    <ProcessTable processes={data.results} sort={sort} onToggleSort={toggleSort} />
                    <Pagination
                        page={data.page}
                        totalPages={data.total_pages}
                        count={data.count}
                        pageSize={data.page_size}
                        onPageChange={goToPage}
                    />
                </div>
            )}
        </div>
    )
}
