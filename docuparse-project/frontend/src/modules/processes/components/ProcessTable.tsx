import { Fragment, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { ProcessSummary } from '../types'
import { ProcessStatusBadge } from './ProcessStatusBadge'
import { ProcessRowDetail } from './ProcessRowDetail'

function ProcessRow({ process }: { process: ProcessSummary }) {
    const [expanded, setExpanded] = useState(false)
    const toggle = () => setExpanded((value) => !value)

    return (
        <Fragment>
            <tr
                onClick={toggle}
                className={`cursor-pointer border-t border-zinc-100 hover:bg-zinc-50 ${
                    expanded ? 'bg-zinc-50' : 'bg-white'
                }`}
            >
                <td className="px-4 py-3">
                    <button
                        type="button"
                        onClick={(event) => {
                            event.stopPropagation()
                            toggle()
                        }}
                        aria-expanded={expanded}
                        className="flex items-center gap-2 text-left text-sm font-medium text-zinc-800"
                    >
                        {expanded ? (
                            <ChevronDown size={16} aria-hidden="true" className="shrink-0 text-zinc-400" />
                        ) : (
                            <ChevronRight size={16} aria-hidden="true" className="shrink-0 text-zinc-400" />
                        )}
                        <span className="truncate">{process.original_filename || process.id}</span>
                    </button>
                </td>
                <td className="px-4 py-3">
                    <ProcessStatusBadge label={process.status_label} />
                </td>
            </tr>
            {expanded ? (
                <tr>
                    <td colSpan={2} className="p-0">
                        <ProcessRowDetail documentId={process.id} />
                    </td>
                </tr>
            ) : null}
        </Fragment>
    )
}

export function ProcessTable({ processes }: { processes: ProcessSummary[] }) {
    return (
        <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white">
            <table className="w-full min-w-[480px] border-collapse text-sm">
                <thead>
                    <tr className="text-left text-xs font-semibold uppercase tracking-wide text-zinc-500">
                        <th scope="col" className="px-4 py-3">
                            Processo
                        </th>
                        <th scope="col" className="px-4 py-3">
                            Status
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {processes.map((process) => (
                        <ProcessRow key={process.id} process={process} />
                    ))}
                </tbody>
            </table>
        </div>
    )
}
