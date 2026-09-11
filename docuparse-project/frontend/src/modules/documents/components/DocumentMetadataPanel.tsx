import type { ChannelMetadata, Document } from '../types'

export function DocumentMetadataPanel({ document }: { document: Document }) {
    const meta = (document.metadata_channel ?? document.metadata?.metadata_channel ?? {}) as ChannelMetadata
    // Só o que ajuda a identificar de onde o documento veio — nada de IDs
    // internos (código do processo, Message-ID) ou nomes técnicos de provedor.
    const rows = [
        { label: 'Remetente', value: meta.sender },
        { label: 'Destinatário', value: meta.to },
        { label: 'Assunto', value: meta.subject },
        { label: 'Data de envio', value: meta.date },
    ].filter((row) => row.value != null && row.value !== '')

    const attachments = Array.isArray(meta.attachments) ? meta.attachments : meta.attachments ? [meta.attachments] : []

    const isEmpty = rows.length === 0 && attachments.length === 0
    if (isEmpty) return null

    return (
        <div className="rounded-md border border-zinc-200">
            <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">Origem do documento</div>
            <div className="grid grid-cols-1 gap-3 p-3 sm:grid-cols-2 lg:grid-cols-3">
                {rows.map((row) => (
                    <div key={row.label}>
                        <span className="mb-1 block min-h-8 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                            {row.label}
                        </span>
                        <div className="break-words text-sm text-zinc-800">{row.value}</div>
                    </div>
                ))}
                {attachments.length > 0 ? (
                    <div className="col-span-full">
                        <span className="mb-1 block min-h-8 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                            Anexos
                        </span>
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
        </div>
    )
}
