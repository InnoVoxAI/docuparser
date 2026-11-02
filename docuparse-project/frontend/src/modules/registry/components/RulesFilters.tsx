import { SearchInput } from '../../../shared/components'
import type { Chart } from '../schemas/registry'
import type { RuleFilters } from '../schemas/rules'

const SELECT = 'h-8 rounded-md border border-zinc-300 bg-white px-2 text-sm'

/** Plano, busca e filtros da lista de regras. */
export function RulesFilters({
    charts,
    chartId,
    filters,
    search,
    onChart,
    onSearch,
    onFilter,
}: {
    charts: Chart[]
    chartId: string
    filters: RuleFilters
    search: string
    onChart: (id: string) => void
    onSearch: (value: string) => void
    onFilter: (patch: Partial<RuleFilters>) => void
}) {
    return (
        <div className="flex flex-wrap items-center gap-2">
            <select
                aria-label="Plano de contas"
                className={SELECT}
                value={chartId}
                onChange={(e) => onChart(e.target.value)}
            >
                {charts.map((chart) => (
                    <option key={chart.id} value={chart.id}>
                        {chart.name}
                    </option>
                ))}
            </select>
            <SearchInput value={search} onChange={onSearch} placeholder="Buscar CNPJ, nome ou conta" />
            <select
                aria-label="Origem"
                className={SELECT}
                value={filters.origin}
                onChange={(e) => onFilter({ origin: e.target.value as RuleFilters['origin'] })}
            >
                <option value="">Todas as origens</option>
                <option value="history">Histórico do ERP</option>
                <option value="learned">Aprendida com analistas</option>
                <option value="manual">Manual</option>
            </select>
            <select
                aria-label="Pré-preenche"
                className={SELECT}
                value={filters.prefills}
                onChange={(e) => onFilter({ prefills: e.target.value as RuleFilters['prefills'] })}
            >
                <option value="">Pré-preenche: todas</option>
                <option value="true">Só as que pré-preenchem</option>
                <option value="false">Só as que não pré-preenchem</option>
            </select>
        </div>
    )
}
