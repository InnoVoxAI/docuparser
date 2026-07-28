import type { ChangeEvent } from 'react'
import { Eye } from 'lucide-react'
import { StatusBadge } from '../../../shared/components'
import { formatDate } from '../../../shared/utils'
import type { Document, EmailModalDoc } from '../types'

export function DocumentTableRow({
    document,
    compact,
    selectable,
    isChecked,
    isSelected,
    onSelectDocument,
    onToggleOne,
    onOpenEmailModal,
}: {
    document: Document
    compact: boolean
    selectable: boolean
    isChecked: boolean
    isSelected: boolean
    onSelectDocument: (id: string) => void
    onToggleOne: (e: ChangeEvent<HTMLInputElement>, id: string) => void
    onOpenEmailModal: (doc: EmailModalDoc) => void
}) {
    return (
        <tr
            onClick={() => onSelectDocument(document.id)}
            className={`cursor-pointer border-b border-zinc-100 hover:bg-zinc-50 ${
                isChecked ? 'bg-zinc-50' : isSelected ? 'bg-zinc-100' : ''
            }`}
        >
            {selectable ? (
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                    <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) => onToggleOne(e, document.id)}
                        className="h-4 w-4 cursor-pointer rounded border-zinc-300 accent-zinc-700"
                        aria-label={`Selecionar ${document.original_filename || document.id}`}
                    />
                </td>
            ) : null}
            <td className="px-3 py-2 font-medium">{document.original_filename || document.id}</td>
            <td className="px-3 py-2">
                <StatusBadge status={document.status} />
            </td>
            {compact ? null : <td className="px-3 py-2">{document.channel || '-'}</td>}
            {compact ? null : <td className="px-3 py-2">{document.document_type || '-'}</td>}
            <td className="px-3 py-2 text-zinc-500">{formatDate(document.updated_at || document.received_at)}</td>
            {compact ? null : (
                <td className="px-3 py-2 text-zinc-500">
                    {document.status === 'APPROVED'
                        ? formatDate(document.approved_at)
                        : document.status === 'REJECTED'
                          ? formatDate(document.rejected_at)
                          : null}
                </td>
            )}
            <td className="px-2 py-2" onClick={(e) => e.stopPropagation()}>
                <button
                    type="button"
                    title="Ver informações do documento"
                    onClick={() =>
                        onOpenEmailModal({
                            id: document.id,
                            filename: document.original_filename || document.id,
                            channel: document.channel,
                            content_type: document.content_type,
                            metadata_channel: document.metadata_channel,
                        })
                    }
                    className="flex h-6 w-6 items-center justify-center rounded text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
                >
                    <Eye size={14} aria-hidden="true" />
                </button>
            </td>
        </tr>
    )
}
