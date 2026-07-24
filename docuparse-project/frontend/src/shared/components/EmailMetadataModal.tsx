import { X } from 'lucide-react'
import type { ChannelMetadata, EmailModalDoc } from '../../types'
import { DocumentBlobPreview } from './DocumentBlobPreview'

export function EmailMetadataModal({ data, onClose }: { data: EmailModalDoc; onClose: () => void }) {
    const isEmail = data.channel === 'email'
    const isWhatsApp = data.channel === 'whatsapp'
    const meta = (data.metadata_channel || {}) as ChannelMetadata

    const channelRows = isEmail
        ? [
              { label: 'Remetente', value: meta.sender },
              { label: 'Para', value: meta.to },
              { label: 'CC', value: meta.cc },
              { label: 'Assunto', value: meta.subject },
              { label: 'Data de envio', value: meta.date },
              { label: 'Message-ID', value: meta.message_id },
              { label: 'Provedor', value: meta.provider },
          ].filter((row) => row.value)
        : isWhatsApp
          ? [
                { label: 'Número que recebeu', value: meta.to_number },
                { label: 'Número que enviou', value: meta.sender },
                { label: 'Message SID', value: meta.message_sid },
                { label: 'Provedor', value: meta.provider },
            ].filter((row) => row.value)
          : []

    const rows = [{ label: 'Código de Processo', value: data.id }, ...channelRows].filter((row) => row.value)

    const modalTitle = isEmail
        ? 'Metadados do email'
        : isWhatsApp
          ? 'Metadados do WhatsApp'
          : 'Informações do documento'

    const noMetaWarning = isEmail
        ? 'Metadados do email nao disponiveis para este documento. Reimporte-o para capturar as informacoes.'
        : isWhatsApp
          ? 'Metadados do WhatsApp nao disponiveis para este documento. Reimporte-o para capturar as informacoes.'
          : null

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
            onClick={(e) => {
                if (e.target === e.currentTarget) onClose()
            }}
            onKeyDown={(e) => {
                if (e.key === 'Escape') onClose()
            }}
            role="button"
            tabIndex={0}
            aria-label="Fechar modal"
        >
            <div className="relative mx-4 max-h-[90vh] w-full max-w-4xl overflow-auto rounded-lg border border-zinc-200 bg-white shadow-xl">
                <div className="flex items-center justify-between border-b border-zinc-200 px-5 py-4">
                    <div className="min-w-0 flex-1 pr-4">
                        <div className="text-sm font-semibold">{modalTitle}</div>
                        {data.filename ? (
                            <div className="mt-0.5 text-xs text-zinc-500 truncate">{data.filename}</div>
                        ) : null}
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="shrink-0 rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
                    >
                        <X size={16} aria-hidden="true" />
                    </button>
                </div>
                {/* feature 009: as informações existentes ficam à esquerda e a
                    pré-visualização do documento é ADICIONADA à direita (sem
                    remover nada — FR-012/FR-019). */}
                <div className="grid md:grid-cols-2">
                    <div className="min-w-0 md:border-r md:border-zinc-200">
                        {(isEmail || isWhatsApp) && channelRows.length === 0 ? (
                            <div className="divide-y divide-zinc-100 px-5 py-2">
                                <div className="grid grid-cols-[140px_1fr] gap-3 py-2 text-sm">
                                    <dt className="font-medium text-zinc-500">Código de Processo</dt>
                                    <dd className="min-w-0 break-all text-zinc-800">{data.id}</dd>
                                </div>
                                {noMetaWarning ? (
                                    <div className="py-4 text-sm text-zinc-500">{noMetaWarning}</div>
                                ) : null}
                            </div>
                        ) : (
                            <div className="divide-y divide-zinc-100 px-5 py-2">
                                {rows.map(({ label, value }) => (
                                    <div key={label} className="grid grid-cols-[140px_1fr] gap-3 py-2 text-sm">
                                        <dt className="font-medium text-zinc-500">{label}</dt>
                                        <dd className="min-w-0 break-all text-zinc-800">{value}</dd>
                                    </div>
                                ))}
                            </div>
                        )}
                        {Array.isArray(meta.attachments) && meta.attachments.length > 0 ? (
                            <div className="border-t border-zinc-200 px-5 py-3">
                                <div className="mb-1.5 text-xs font-semibold uppercase text-zinc-500">Anexos</div>
                                <ul className="space-y-1">
                                    {meta.attachments.map((name: unknown, i: number) => (
                                        <li key={i} className="flex items-center gap-1.5 text-sm text-zinc-700">
                                            <span className="text-zinc-400">·</span>
                                            {String(name)}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ) : null}
                        {meta.body_text ? (
                            <div className="border-t border-zinc-200 px-5 py-3">
                                <div className="mb-1 text-xs font-semibold uppercase text-zinc-500">Corpo do email</div>
                                <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-zinc-50 p-3 text-xs text-zinc-700">
                                    {meta.body_text}
                                </pre>
                            </div>
                        ) : null}
                        {isWhatsApp && meta.body ? (
                            <div className="border-t border-zinc-200 px-5 py-3">
                                <div className="mb-1 text-xs font-semibold uppercase text-zinc-500">
                                    Mensagem de texto
                                </div>
                                <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-zinc-50 p-3 text-xs text-zinc-700">
                                    {meta.body}
                                </pre>
                            </div>
                        ) : null}
                    </div>
                    <div className="min-w-0 border-t border-zinc-200 px-5 py-4 md:border-t-0">
                        <div className="mb-2 text-xs font-semibold uppercase text-zinc-500">Documento original</div>
                        <DocumentBlobPreview
                            documentId={data.id}
                            contentType={data.content_type}
                            filename={data.filename}
                        />
                    </div>
                </div>
                <div className="border-t border-zinc-200 px-5 py-3 text-right">
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-100"
                    >
                        Fechar
                    </button>
                </div>
            </div>
        </div>
    )
}
