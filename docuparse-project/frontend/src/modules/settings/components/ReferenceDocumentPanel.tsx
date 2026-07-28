import { Field, SearchInput } from '../../../shared/components'
import type { Document, SchemaField } from '../../../types'
import { useDocumentsQuery } from '../../documents'
import type { ReferenceReview } from '../types'
import { DocumentPreview } from './DocumentPreview'
import { HighlightedOcrText } from './HighlightedOcrText'

/**
 * O seletor de documento de referência usava `useDocumentPage` (hoje morto
 * em `main.tsx`, ver T036-T040). Passa a usar `useDocumentsQuery` do módulo
 * `documents`, via barrel — a mesma dependência cruzada legítima já
 * documentada em `contracts/module-boundaries.md` ("settings ... Consumido
 * por: modules/documents", e o inverso aqui: settings consome documents).
 */
export function ReferenceDocumentPanel({
    selectedDocumentId,
    onSelectDocument,
    referenceDocument,
    fields,
    review,
    onReviewChange,
}: {
    selectedDocumentId: string
    onSelectDocument: (id: string) => void
    referenceDocument: Document | null
    fields: SchemaField[]
    review: ReferenceReview
    onReviewChange: (review: ReferenceReview) => void
}) {
    const { search, setSearch, data } = useDocumentsQuery()

    return (
        <div className="space-y-4">
            <div className="grid gap-4 xl:grid-cols-[360px_minmax(360px,1fr)_minmax(360px,1fr)]">
                <section className="rounded-md border border-zinc-200">
                    <div className="flex flex-col gap-2 border-b border-zinc-200 px-3 py-2">
                        <div className="text-sm font-semibold">Documento de referencia</div>
                        <SearchInput value={search} onChange={setSearch} placeholder="Buscar..." />
                    </div>
                    <div className="max-h-[520px] overflow-auto">
                        {data.results.map((document) => (
                            <button
                                key={document.id}
                                type="button"
                                onClick={() => onSelectDocument(document.id)}
                                className={`block w-full border-b border-zinc-100 px-3 py-2 text-left text-sm hover:bg-zinc-50 ${selectedDocumentId === document.id ? 'bg-zinc-100' : ''}`}
                            >
                                <div className="font-medium">{document.original_filename || document.id}</div>
                                <div className="mt-1 text-xs text-zinc-500">
                                    {document.document_type || '-'} · {document.channel || '-'}
                                </div>
                            </button>
                        ))}
                    </div>
                </section>
                <DocumentPreview document={referenceDocument} />
                <HighlightedOcrText text={referenceDocument?.full_transcription || ''} fields={fields} examples={[]} />
            </div>
            <section className="rounded-md border border-zinc-200 bg-white p-4">
                <div className="mb-3 text-sm font-semibold">Revisao da qualidade do OCR</div>
                <div className="grid gap-3 lg:grid-cols-[220px_260px_1fr]">
                    <Field label="Texto confere?">
                        <select
                            value={review.quality}
                            onChange={(event) => onReviewChange({ ...review, quality: event.target.value })}
                            className="input"
                        >
                            <option value="pending">Nao revisado</option>
                            <option value="matches">Confere com o documento</option>
                            <option value="minor_issues">Tem pequenas divergencias</option>
                            <option value="major_issues">Nao confere</option>
                        </select>
                    </Field>
                    <Field label="Acao recomendada">
                        <select
                            value={review.action}
                            onChange={(event) => onReviewChange({ ...review, action: event.target.value })}
                            className="input"
                        >
                            <option value="review_before_examples">Revisar antes de criar exemplos</option>
                            <option value="use_as_reference">Usar como referencia</option>
                            <option value="reprocess_ocr">Reprocessar OCR</option>
                            <option value="replace_document">Trocar documento</option>
                            <option value="manual_transcription">Corrigir transcricao manualmente</option>
                        </select>
                    </Field>
                    <Field label="Observacoes">
                        <textarea
                            value={review.notes}
                            onChange={(event) => onReviewChange({ ...review, notes: event.target.value })}
                            className="input min-h-[86px]"
                            placeholder="Registre linhas faltantes, campos incorretos, leitura manuscrita ruim ou motivo para reprocessar."
                        />
                    </Field>
                </div>
            </section>
        </div>
    )
}
