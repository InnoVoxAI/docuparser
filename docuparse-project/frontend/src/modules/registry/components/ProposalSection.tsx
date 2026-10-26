import type { Proposal, ProposalAction } from '../schemas/registry'
import { ACTION_LABELS } from '../utils'
import { ProposalDetails } from './ProposalDetails'

const btn = 'h-8 rounded-md border px-2 text-xs font-medium disabled:opacity-50'

interface Props {
    action: ProposalAction
    items: Proposal[]
    selected: ReadonlySet<string>
    canDecide: boolean
    busy: boolean
    onToggle: (id: string) => void
    onToggleAll: (ids: string[], checked: boolean) => void
    onApprove: (proposal: Proposal) => void
    onReject: (proposal: Proposal) => void
    onResolve: (proposal: Proposal) => void
    /** Confirma todas as linhas listadas na seção (pede confirmação antes). Conflitos não têm. */
    onApproveAll: (ids: string[]) => void
    /** Rótulo do que "todas" significa agora: "todos", "os filtrados" ou "desta página". */
    scopeLabel: string
}

export function ProposalSection({
    action,
    items,
    selected,
    canDecide,
    busy,
    onToggle,
    onToggleAll,
    onApprove,
    onReject,
    onResolve,
    onApproveAll,
    scopeLabel,
}: Props) {
    const isConflict = action === 'conflict'
    const ids = items.map((item) => item.id)
    const allSelected = ids.length > 0 && ids.every((id) => selected.has(id))

    return (
        <section aria-label={ACTION_LABELS[action]} className="rounded-md border border-zinc-200">
            <div className="flex items-center justify-between gap-2 border-b border-zinc-200 px-3 py-2">
                <div className="text-sm font-semibold">
                    {ACTION_LABELS[action]} ({items.length})
                </div>
                {isConflict || !canDecide ? null : (
                    <button
                        type="button"
                        disabled={busy}
                        onClick={() => onApproveAll(ids)}
                        className="h-8 rounded-md border border-zinc-300 px-3 text-xs font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50"
                    >
                        Confirmar {scopeLabel} ({items.length})
                    </button>
                )}
            </div>
            <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-zinc-500">
                    <tr>
                        <th className="w-10 px-3 py-2">
                            {isConflict || !canDecide ? null : (
                                <input
                                    type="checkbox"
                                    aria-label={`Selecionar todos: ${ACTION_LABELS[action]}`}
                                    checked={allSelected}
                                    onChange={(event) => onToggleAll(ids, event.target.checked)}
                                />
                            )}
                        </th>
                        <th className="px-3 py-2 font-semibold">Proposta</th>
                        <th className="w-48 px-3 py-2 text-right font-semibold">Ação</th>
                    </tr>
                </thead>
                <tbody>
                    {items.map((proposal) => (
                        <tr key={proposal.id} className="border-t border-zinc-100 align-top">
                            <td className="px-3 py-2">
                                {isConflict || !canDecide ? null : (
                                    <input
                                        type="checkbox"
                                        aria-label={`Selecionar ${proposal.external_id}`}
                                        checked={selected.has(proposal.id)}
                                        onChange={() => onToggle(proposal.id)}
                                    />
                                )}
                            </td>
                            <td className="px-3 py-2">
                                <ProposalDetails proposal={proposal} />
                            </td>
                            <td className="px-3 py-2 text-right">
                                <div className="flex justify-end gap-2">
                                    {isConflict ? (
                                        <button
                                            type="button"
                                            disabled={!canDecide || busy}
                                            onClick={() => onResolve(proposal)}
                                            className={`${btn} border-zinc-900 bg-zinc-900 text-white hover:bg-zinc-700`}
                                        >
                                            Resolver
                                        </button>
                                    ) : (
                                        <button
                                            type="button"
                                            disabled={!canDecide || busy}
                                            onClick={() => onApprove(proposal)}
                                            className={`${btn} border-zinc-900 bg-zinc-900 text-white hover:bg-zinc-700`}
                                        >
                                            Confirmar
                                        </button>
                                    )}
                                    <button
                                        type="button"
                                        disabled={!canDecide || busy}
                                        onClick={() => onReject(proposal)}
                                        className={`${btn} border-zinc-300 text-zinc-700 hover:bg-zinc-100`}
                                    >
                                        Rejeitar
                                    </button>
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </section>
    )
}
