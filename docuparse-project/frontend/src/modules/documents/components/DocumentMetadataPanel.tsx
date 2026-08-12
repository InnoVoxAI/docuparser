import { FileText } from 'lucide-react'
import { EmptyState } from '../../../shared/components'
import type { ChannelMetadata, Document } from '../types'

export function DocumentMetadataPanel({ document }: { document: Document }) {
    const meta = (document.metadata_channel ?? document.metadata?.metadata_channel ?? {}) as ChannelMetadata
    const rows = [
        { label: 'Nome do documento', value: document.original_filename },
        { label: 'Código do processo', value: document.id },
        { label: 'Remetente', value: meta.sender },
        { label: 'Destinatário', value: meta.to },
        { label: 'Assunto', value: meta.subject },
        { label: 'Data de envio', value: meta.date },
        { label: 'Message-ID', value: meta.message_id },
        { label: 'Provedor', value: meta.provider },
        { label: 'Corpo do email', value: meta.body },
    ].filter((row) => row.value != null && row.value !== '')

    const attachments = Array.isArray(meta.attachments) ? meta.attachments : meta.attachments ? [meta.attachments] : []

    const isEmpty = rows.length === 0 && attachments.length === 0

    return (
        <div className="rounded-md border border-zinc-200">
            <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">Metadados do Documento</div>
            {isEmpty ? (
                <EmptyState icon={FileText} text="Nenhum metadado disponível para este documento." />
            ) : (
                <div className="divide-y divide-zinc-100">
                    {rows.map((row) => (
                        <div key={row.label} className="grid grid-cols-[160px_1fr] gap-2 px-3 py-2">
                            <div className="text-xs font-medium text-zinc-500">{row.label}</div>
                            <div className="break-words text-sm text-zinc-800">{row.value}</div>
                        </div>
                    ))}
                    {attachments.length > 0 ? (
                        <div className="grid grid-cols-[160px_1fr] gap-2 px-3 py-2">
                            <div className="text-xs font-medium text-zinc-500">Anexos</div>
                            <div className="space-y-0.5">
                                {attachments.map((a: unknown, i: number) => (
                                    <div key={i} className="text-sm text-zinc-800">
                                        {typeof a === 'object' && a !== null
                                            ? (a as { filename?: string }).filename || JSON.stringify(a)
                                            : String(a)}
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : null}
                </div>
            )}
        </div>
    )
}
