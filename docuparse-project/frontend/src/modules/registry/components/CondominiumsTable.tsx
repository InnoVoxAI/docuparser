import { useMemo, useState } from 'react'
import { Building2 } from 'lucide-react'
import { EmptyState, SearchInput } from '../../../shared/components'
import type { Chart, Condominium } from '../schemas/registry'
import { formatCnpj } from '../utils'

function matches(condominium: Condominium, term: string): boolean {
    if (!term) return true
    const haystack = `${condominium.name} ${condominium.cnpj} ${formatCnpj(condominium.cnpj)}`.toLowerCase()
    return haystack.includes(term.toLowerCase())
}

export function CondominiumsTable({ condominiums, charts }: { condominiums: Condominium[]; charts: Chart[] }) {
    const [term, setTerm] = useState('')
    const chartNames = useMemo(() => new Map(charts.map((chart) => [chart.id, chart.name])), [charts])
    const rows = condominiums.filter((condominium) => matches(condominium, term))

    return (
        <section aria-label="Condomínios" className="rounded-md border border-zinc-200">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-200 px-3 py-2">
                <div className="text-sm font-semibold">Condomínios ({condominiums.length})</div>
                <SearchInput value={term} onChange={setTerm} placeholder="Buscar por nome ou CNPJ" />
            </div>
            {rows.length === 0 ? (
                <EmptyState
                    icon={Building2}
                    text={condominiums.length === 0 ? 'Nenhum condomínio cadastrado ainda.' : 'Nada encontrado.'}
                />
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="text-xs uppercase text-zinc-500">
                            <tr>
                                <th className="px-3 py-2 font-semibold">Nome</th>
                                <th className="px-3 py-2 font-semibold">CNPJ</th>
                                <th className="px-3 py-2 font-semibold">Plano de contas</th>
                                <th className="px-3 py-2 font-semibold">Origem</th>
                                <th className="px-3 py-2 font-semibold">Situação</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((condominium) => (
                                <tr key={condominium.id} className="border-t border-zinc-100">
                                    <td className="px-3 py-2 font-medium text-zinc-900">{condominium.name}</td>
                                    <td className="px-3 py-2 text-zinc-600">
                                        {condominium.cnpj ? formatCnpj(condominium.cnpj) : '-'}
                                    </td>
                                    <td className="px-3 py-2 text-zinc-600">
                                        {(condominium.chart_of_accounts_id &&
                                            chartNames.get(condominium.chart_of_accounts_id)) ||
                                            'Sem plano'}
                                    </td>
                                    <td className="px-3 py-2 text-zinc-600">
                                        {condominium.external_source === 'superlogica' ? 'Superlógica' : 'Manual'}
                                    </td>
                                    <td className="px-3 py-2 text-zinc-600">
                                        {condominium.is_active ? 'Ativo' : 'Inativo'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    )
}
