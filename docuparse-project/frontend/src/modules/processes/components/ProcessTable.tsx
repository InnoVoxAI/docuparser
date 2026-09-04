import { Fragment, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { formatDate } from '../../../shared/utils'
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
                <td className="px-4 py-3 whitespace-nowrap text-zinc-500">
                    {formatDate(process.last_status_change_at)}
                </td>
            </tr>
            {expanded ? (
                <tr>
                    <td colSpan={3} className="p-0">
                        <ProcessRowDetail documentId={process.id} />
                    </td>
                </tr>
            ) : null}
        </Fragment>
    )
}

export function ProcessTable({ processes }: { processes: ProcessSummary[] }) {
    return (
        <div className="min-h-0 flex-1 overflow-auto rounded-lg border border-zinc-200 bg-white">
            <table className="w-full min-w-[640px] border-collapse text-sm">
                <thead className="sticky top-0 z-10 bg-white">
                    <tr className="border-b border-zinc-200 text-left text-xs font-semibold uppercase tracking-wide text-zinc-500">
                        <th scope="col" className="px-4 py-3">
                            Processo
                        </th>
                        <th scope="col" className="px-4 py-3">
                            Status
                        </th>
                        <th scope="col" className="px-4 py-3">
                            Última atualização
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
