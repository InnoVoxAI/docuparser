import { useEffect } from 'react'
import { api } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import type { Document, SchemaField } from '../../../types'
import type { LayoutForm, SchemaForm } from '../types'
import { buildLangExtractPreview } from '../utils'

/** Carrega o documento de referência ao trocar `selectedDocumentId` (main.tsx ~1119-1147), tal-e-qual. */
export function useReferenceDocumentLoader(
    selectedDocumentId: string,
    fields: SchemaField[],
    setSchemaSelectionSource: (source: string) => void,
    setReferenceDocument: (doc: Document | null) => void,
    setTestOutput: (value: string) => void,
    setSchemaForm: (updater: (current: SchemaForm) => SchemaForm) => void,
    setLayoutForm: (updater: (current: LayoutForm) => LayoutForm) => void,
    setMessage: (value: string) => void,
) {
    useEffect(() => {
        if (!selectedDocumentId) {
            setReferenceDocument(null)
            return
        }
        setSchemaSelectionSource('auto')
        let ignore = false
        api.get<Document>(`/documents/${selectedDocumentId}`)
            .then((response) => {
                if (!ignore) {
                    setReferenceDocument(response.data)
                    setTestOutput(buildLangExtractPreview(response.data.full_transcription || '', fields))
                    const docType = response.data.document_type
                    if (docType) {
                        setSchemaForm((current) => ({ ...current, document_type: docType }))
                        setLayoutForm((current) => ({ ...current, document_type: docType }))
                    }
                }
            })
            .catch((requestError) => {
                if (!ignore) {
                    setMessage(readError(requestError, 'Nao foi possivel carregar o documento de referencia.'))
                }
            })
        return () => {
            ignore = true
        }
    }, [selectedDocumentId])
}
