import type { Proposal } from '../schemas/registry'
import { describeProposal, fieldLabel, formatValue, proposalAccounts, warningLabel } from '../utils'
import { AccountTree } from './AccountTree'

function ChartAccounts({ proposal }: { proposal: Proposal }) {
    const { accounts, orphans } = proposalAccounts(proposal.data)
    if (accounts.length === 0) return null
    return (
        <details className="mt-1">
            <summary className="cursor-pointer text-xs font-medium text-zinc-700 underline">
                Ver as {accounts.length} contas
            </summary>
            <div className="mt-2 rounded-md border border-zinc-100 bg-zinc-50 p-2">
                <AccountTree accounts={accounts} flagged={orphans} />
            </div>
        </details>
    )
}

/** Título, fatos, diferença campo a campo e avisos de uma proposta. */
export function ProposalDetails({ proposal }: { proposal: Proposal }) {
    const { title, facts } = describeProposal(proposal)
    const changes = Object.entries(proposal.diff)

    return (
        <div className="space-y-1">
            <div className="font-medium text-zinc-900">{title}</div>
            <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-0.5 text-xs">
                {facts.map((fact) => (
                    <div key={fact.label} className="contents">
                        <dt className="font-semibold text-zinc-500">{fact.label}</dt>
                        <dd className="text-zinc-700">{fact.value}</dd>
                    </div>
                ))}
            </dl>
            {proposal.entity_type === 'chart' ? <ChartAccounts proposal={proposal} /> : null}
            {changes.length > 0 ? (
                <ul aria-label="Diferenças" className="space-y-0.5 text-xs text-zinc-700">
                    {changes.map(([field, change]) => (
                        <li key={field}>
                            <span className="font-semibold">{fieldLabel(field)}:</span>{' '}
                            <span className="text-zinc-500 line-through">{formatValue(field, change.from)}</span>
                            {' → '}
                            <span>{formatValue(field, change.to)}</span>
                        </li>
                    ))}
                </ul>
            ) : null}
            {proposal.warnings.length > 0 ? (
                <ul aria-label="Avisos" className="flex flex-wrap gap-1">
                    {proposal.warnings.map((warning) => (
                        <li
                            key={warning}
                            className="rounded bg-amber-50 px-2 py-0.5 text-xs text-amber-700 ring-1 ring-amber-200"
                        >
                            {warningLabel(warning)}
                        </li>
                    ))}
                </ul>
            ) : null}
        </div>
    )
}
