import { useState } from 'react'
import { ListTree } from 'lucide-react'
import { Alert, EmptyState } from '../../../shared/components'
import { readError } from '../../../shared/utils'
import { useChartAccounts } from '../hooks'
import type { Chart, Condominium } from '../schemas/registry'
import { AccountTree } from './AccountTree'

function ChartAccounts({ chartId }: { chartId: string }) {
    const { data, isLoading, error } = useChartAccounts(chartId)
    if (isLoading) return <p className="p-3 text-sm text-zinc-500">Carregando contas...</p>
    if (error) return <Alert tone="error">{readError(error, 'Nao foi possivel carregar as contas do plano.')}</Alert>
    if (!data?.length) return <EmptyState icon={ListTree} text="Este plano ainda não tem contas." />
    return <AccountTree accounts={data} />
}

export function ChartsPanel({ charts, condominiums }: { charts: Chart[]; condominiums: Condominium[] }) {
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const usage = (chartId: string) => condominiums.filter((c) => c.chart_of_accounts_id === chartId).length

    return (
        <section aria-label="Planos de contas" className="rounded-md border border-zinc-200">
            <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">
                Planos de contas ({charts.length})
            </div>
            {charts.length === 0 ? (
                <EmptyState icon={ListTree} text="Nenhum plano de contas cadastrado ainda." />
            ) : (
                <div className="grid gap-0 md:grid-cols-[16rem_1fr]">
                    <ul className="border-b border-zinc-100 md:border-b-0 md:border-r">
                        {charts.map((chart) => (
                            <li key={chart.id}>
                                <button
                                    type="button"
                                    onClick={() => setSelectedId(chart.id)}
                                    aria-pressed={selectedId === chart.id}
                                    className={`w-full px-3 py-2 text-left text-sm hover:bg-zinc-50 ${selectedId === chart.id ? 'bg-zinc-100 font-medium' : ''}`}
                                >
                                    <span className="block text-zinc-900">{chart.name}</span>
                                    <span className="text-xs text-zinc-500">
                                        {usage(chart.id)} condomínio(s){chart.is_active ? '' : ' · inativo'}
                                    </span>
                                </button>
                            </li>
                        ))}
                    </ul>
                    <div className="p-3">
                        {selectedId ? (
                            <ChartAccounts chartId={selectedId} />
                        ) : (
                            <p className="text-sm text-zinc-500">Escolha um plano para ver as contas.</p>
                        )}
                    </div>
                </div>
            )}
        </section>
    )
}
