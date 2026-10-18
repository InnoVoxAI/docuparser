import type { Proposal } from '../schemas/registry'
import { describeProposal, fieldLabel, formatValue, warningLabel } from '../utils'

/** Título, diferença campo a campo e avisos de uma proposta. */
export function ProposalDetails({ proposal }: { proposal: Proposal }) {
    const { title, detail } = describeProposal(proposal)
    const changes = Object.entries(proposal.diff)

    return (
        <div className="space-y-1">
            <div className="font-medium text-zinc-900">{title}</div>
            {detail ? <div className="text-xs text-zinc-500">{detail}</div> : null}
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
