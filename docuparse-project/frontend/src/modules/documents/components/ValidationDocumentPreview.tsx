import { FileText } from 'lucide-react'
import { DocumentBlobPreview, EmptyState } from '../../../shared/components'
import type { Document } from '../types'

export function ValidationDocumentPreview({
    selectedDocument,
    fillHeight = false,
}: {
    selectedDocument: Document | null
    /** Ocupa a altura toda do container em vez de uma altura fixa — usado no
     * drawer expandido, onde o painel fica lado a lado com os campos. */
    fillHeight?: boolean
}) {
    return (
        <section
            className={
                fillHeight
                    ? 'flex h-full min-h-0 flex-col rounded-md border border-zinc-200 bg-white'
                    : 'min-h-[360px] rounded-md border border-zinc-200 bg-white'
            }
        >
            <div className="shrink-0 border-b border-zinc-200 px-4 py-3 text-sm font-semibold">
                {selectedDocument?.original_filename || selectedDocument?.id || 'Documento'}
            </div>
            {!selectedDocument ? (
                <EmptyState icon={FileText} text="Selecione um documento para visualizar." />
            ) : fillHeight ? (
                <div className="min-h-0 flex-1">
                    <DocumentBlobPreview
                        documentId={selectedDocument.id}
                        contentType={selectedDocument.content_type}
                        filename={selectedDocument.original_filename}
                        frameClassName="h-full w-full"
                    />
                </div>
            ) : (
                // Carrega o arquivo como blob autenticado (contorna X-Frame-Options em produção).
                <DocumentBlobPreview
                    documentId={selectedDocument.id}
                    contentType={selectedDocument.content_type}
                    filename={selectedDocument.original_filename}
                    frameClassName="h-[620px] w-full"
                />
            )}
        </section>
    )
}
