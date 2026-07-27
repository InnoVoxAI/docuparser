import { FileText } from 'lucide-react'
import { DocumentBlobPreview, EmptyState } from '../../../shared/components'
import type { Document } from '../types'

export function ValidationDocumentPreview({ selectedDocument }: { selectedDocument: Document | null }) {
    return (
        <section className="min-h-[360px] rounded-md border border-zinc-200 bg-white">
            <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
                <div className="text-sm font-semibold">
                    {selectedDocument?.original_filename || selectedDocument?.id || 'Documento'}
                </div>
                {selectedDocument ? (
                    <a
                        href={`/api/ocr/documents/${selectedDocument.id}/file`}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-100"
                    >
                        Abrir
                    </a>
                ) : null}
            </div>
            {!selectedDocument ? (
                <EmptyState icon={FileText} text="Selecione um documento para visualizar." />
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
