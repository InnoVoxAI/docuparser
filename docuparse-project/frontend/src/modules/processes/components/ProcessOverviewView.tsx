import { useNavigate } from 'react-router'
import { Plus, Workflow } from 'lucide-react'
import { Alert, EmptyState, Pagination, SearchInput } from '../../../shared/components'
import { navPath } from '../../../shared/utils'
import { useProcessesQuery } from '../hooks/useProcessesQuery'
import { ProcessFilters } from './ProcessFilters'
import { ProcessTable } from './ProcessTable'

/** Página inicial do app: tabela de processos, busca e filtro por status e
 * acesso ao envio de um novo documento. Sem cabeçalho/sidebar — só o conteúdo. */
export function ProcessOverviewView() {
    const navigate = useNavigate()
    const { data, loading, error, statusGroup, setStatusGroup, search, setSearch, goToPage } = useProcessesQuery()

    return (
        <div className="mx-auto flex min-h-0 w-full max-w-5xl flex-1 flex-col gap-4">
            <div className="flex flex-wrap items-end justify-between gap-3 shrink-0">
                <div className="flex flex-wrap items-end gap-3">
                    <ProcessFilters selected={statusGroup} onChange={setStatusGroup} />
                    <SearchInput value={search} onChange={setSearch} placeholder="Buscar por nome do arquivo..." />
                </div>
                <button type="button" onClick={() => navigate(navPath('upload'))} className="primary-button">
                    <Plus size={16} aria-hidden="true" />
                    Novo processo
                </button>
            </div>

            {error ? <Alert tone="error">{error}</Alert> : null}

            {loading && data.results.length === 0 ? (
                <Alert>Carregando processos...</Alert>
            ) : data.results.length === 0 ? (
                <div className="rounded-lg border border-zinc-200 bg-white">
                    <EmptyState icon={Workflow} text="Nenhum processo encontrado para o filtro selecionado." />
                </div>
            ) : (
                <div className="flex min-h-0 flex-1 flex-col gap-3">
                    <ProcessTable processes={data.results} />
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
