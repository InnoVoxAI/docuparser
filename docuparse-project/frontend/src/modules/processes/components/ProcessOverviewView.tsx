import { useNavigate } from 'react-router'
import { Plus, Workflow } from 'lucide-react'
import { Alert, EmptyState, Pagination } from '../../../shared/components'
import { navPath } from '../../../shared/utils'
import { useProcessesQuery } from '../hooks/useProcessesQuery'
import { ProcessFilters } from './ProcessFilters'
import { ProcessTable } from './ProcessTable'

/** Página inicial do app: tabela de processos com filtros por status e acesso
 * ao envio de um novo documento. */
export function ProcessOverviewView() {
    const navigate = useNavigate()
    const { data, loading, error, statusGroups, toggleStatusGroup, clearStatusGroups, goToPage } = useProcessesQuery()

    return (
        <div className="mx-auto flex max-w-5xl flex-col gap-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h1 className="text-xl font-semibold text-zinc-900">Processos</h1>
                    <p className="mt-1 text-sm text-zinc-500">
                        Acompanhe cada documento enviado e resolva o que estiver aguardando ação.
                    </p>
                </div>
                <button type="button" onClick={() => navigate(navPath('upload'))} className="primary-button">
                    <Plus size={16} aria-hidden="true" />
                    Novo processo
                </button>
            </div>

            <ProcessFilters selected={statusGroups} onToggle={toggleStatusGroup} onClear={clearStatusGroups} />

            {error ? <Alert tone="error">{error}</Alert> : null}

            {loading && data.results.length === 0 ? (
                <Alert>Carregando processos...</Alert>
            ) : data.results.length === 0 ? (
                <div className="rounded-lg border border-zinc-200 bg-white">
                    <EmptyState icon={Workflow} text="Nenhum processo encontrado para os filtros selecionados." />
                </div>
            ) : (
                <div className="flex flex-col gap-3">
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
