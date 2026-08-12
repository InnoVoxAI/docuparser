import { FileText } from 'lucide-react'
import { DocumentBlobPreview, EmptyState } from '../../../shared/components'
import type { Document } from '../../../types'

export function DocumentPreview({ document }: { document: Document | null }) {
    return (
        <section className="rounded-md border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-3 py-2 text-sm font-semibold">Original</div>
            {!document ? (
                <EmptyState icon={FileText} text="Selecione um documento." />
            ) : (
                // Carrega o arquivo como blob autenticado (contorna X-Frame-Options em produção).
                <DocumentBlobPreview
                    documentId={document.id}
                    contentType={document.content_type}
                    filename={document.original_filename}
                    frameClassName="h-[520px] w-full"
                />
            )}
        </section>
    )
}
