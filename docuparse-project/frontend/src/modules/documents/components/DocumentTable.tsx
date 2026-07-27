import { useState, type ChangeEvent } from 'react'
import { FileText } from 'lucide-react'
import { EmptyState, EmailMetadataModal } from '../../../shared/components'
import type { Document, EmailModalDoc } from '../types'
import { DocumentTableHead } from './DocumentTableHead'
import { DocumentTableRow } from './DocumentTableRow'

export function DocumentTable({
    documents,
    selectedDocumentId = '',
    onSelectDocument,
    compact = false,
    selectable = false,
    bulkSelectedIds = null,
    onBulkSelectionChange = null,
}: {
    documents: Document[]
    selectedDocumentId?: string
    onSelectDocument: (id: string) => void
    compact?: boolean
    selectable?: boolean
    bulkSelectedIds?: Set<string> | null
    onBulkSelectionChange?: ((ids: Set<string>) => void) | null
}) {
    const [sortKey, setSortKey] = useState<string | null>(null)
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
    const [emailModalDoc, setEmailModalDoc] = useState<EmailModalDoc | null>(null)

    function handleSort(key: string) {
        if (sortKey === key) {
            setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
        } else {
            setSortKey(key)
            setSortDir('asc')
        }
    }

    const sortedDocuments = sortKey
        ? [...documents].sort((a, b) => {
              let aVal = '',
                  bVal = ''
              if (sortKey === 'arquivo') {
                  aVal = (a.original_filename || a.id || '').toLowerCase()
                  bVal = (b.original_filename || b.id || '').toLowerCase()
              } else if (sortKey === 'status') {
                  aVal = (a.status || '').toLowerCase()
                  bVal = (b.status || '').toLowerCase()
              } else if (sortKey === 'canal') {
                  aVal = (a.channel || '').toLowerCase()
                  bVal = (b.channel || '').toLowerCase()
              } else if (sortKey === 'tipo') {
                  aVal = (a.document_type || '').toLowerCase()
                  bVal = (b.document_type || '').toLowerCase()
              } else if (sortKey === 'atualizado') {
                  aVal = a.updated_at || a.received_at || ''
                  bVal = b.updated_at || b.received_at || ''
              }
              if (aVal < bVal) return sortDir === 'asc' ? -1 : 1
              if (aVal > bVal) return sortDir === 'asc' ? 1 : -1
              return 0
          })
        : documents

    const allSelected =
        selectable && sortedDocuments.length > 0 && sortedDocuments.every((d) => bulkSelectedIds?.has(d.id))
    const someSelected = selectable && !allSelected && sortedDocuments.some((d) => bulkSelectedIds?.has(d.id))

    function toggleAll(e: ChangeEvent<HTMLInputElement>) {
        e.stopPropagation()
        if (!onBulkSelectionChange) return
        const next = new Set(bulkSelectedIds)
        if (allSelected) {
            sortedDocuments.forEach((d) => next.delete(d.id))
        } else {
            sortedDocuments.forEach((d) => next.add(d.id))
        }
        onBulkSelectionChange(next)
    }

    function toggleOne(e: ChangeEvent<HTMLInputElement>, id: string) {
        e.stopPropagation()
        if (!onBulkSelectionChange) return
        const next = new Set(bulkSelectedIds)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        onBulkSelectionChange(next)
    }

    if (documents.length === 0) {
        return <EmptyState icon={FileText} text="Nenhum documento encontrado." />
    }

    return (
        <>
            <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] border-collapse text-sm">
                    <DocumentTableHead
                        compact={compact}
                        selectable={selectable}
                        sortKey={sortKey}
                        sortDir={sortDir}
                        onSort={handleSort}
                        allSelected={allSelected}
                        someSelected={someSelected}
                        onToggleAll={toggleAll}
                    />
                    <tbody>
                        {sortedDocuments.map((document) => (
                            <DocumentTableRow
                                key={document.id}
                                document={document}
                                compact={compact}
                                selectable={selectable}
                                isChecked={bulkSelectedIds?.has(document.id) ?? false}
                                isSelected={selectedDocumentId === document.id}
                                onSelectDocument={onSelectDocument}
                                onToggleOne={toggleOne}
                                onOpenEmailModal={setEmailModalDoc}
                            />
                        ))}
                    </tbody>
                </table>
            </div>
            {emailModalDoc ? <EmailMetadataModal data={emailModalDoc} onClose={() => setEmailModalDoc(null)} /> : null}
        </>
    )
}
