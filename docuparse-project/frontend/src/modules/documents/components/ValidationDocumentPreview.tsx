import { FileText } from 'lucide-react'
import { DocumentBlobPreview, EmptyState } from '../../../shared/components'
import type { Document } from '../types'

export function ValidationDocumentPreview({ selectedDocument }: { selectedDocument: Document | null }) {
    return (
        <section className="min-h-[360px] rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">
                {selectedDocument?.original_filename || selectedDocument?.id || 'Documento'}
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
