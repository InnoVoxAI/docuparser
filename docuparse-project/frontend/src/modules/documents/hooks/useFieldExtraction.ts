import { useEffect, useState } from 'react'
import { api } from '../../../shared/lib/http'
import { readError } from '../../../shared/utils'
import { deriveFieldRowsFromFields, pollDocumentExtraction } from '../utils'
import type { Document, ExtractionResult, FieldRow, SchemaConfig } from '../types'

/**
 * Popula `fieldRows` a partir do `extraction_result` persistido (ou detecção
 * de schema por texto, se nunca extraído) e expõe `runLangExtract` — extraído
 * de `ValidationView` só para respeitar o limite de 150 linhas/arquivo
 * (FR-012/SC-002), não por reuso: é estado de uma única tela.
 */
export function useFieldExtraction({
    schemas,
    selectedDocument,
    selectedDocumentId,
}: {
    schemas: SchemaConfig[]
    selectedDocument: Document | null
    selectedDocumentId: string
}) {
    const [fieldRows, setFieldRows] = useState<FieldRow[]>([])
    const [selectedSchemaId, setSelectedSchemaId] = useState('')
    const [extracting, setExtracting] = useState(false)
    const [extractMessage, setExtractMessage] = useState('')

    useEffect(() => {
        const result = selectedDocument?.extraction_result
        const isLangExtracted = result && result.schema_id !== 'legacy_ocr'
        const persistedFields = isLangExtracted ? result.fields : null
        if (persistedFields && Object.keys(persistedFields).length > 0) {
            setFieldRows(deriveFieldRowsFromFields(persistedFields))
        } else {
            setFieldRows([])
        }
        setExtractMessage('')

        // Auto-select the schema model: prefer the one used in the last extraction,
        // then fall back to backend text classification.
        if (isLangExtracted && result.schema_id) {
            const match = schemas.find((s) => s.schema_id === result.schema_id)
            if (match) {
                setSelectedSchemaId(match.id)
                return
            }
        }
        const rawText = selectedDocument?.full_transcription || ''
        if (!rawText) return

        let ignore = false
        api.post<{ schema_id?: string }>('/classify-text', { text: rawText })
            .then((res) => {
                if (ignore) return
                const schemaId = res.data?.schema_id
                if (!schemaId) return
                const s = schemas.find((sc) => sc.schema_id === schemaId)
                if (s) setSelectedSchemaId(s.id)
            })
            .catch(() => {})
        return () => {
            ignore = true
        }
    }, [selectedDocument?.id])

    const applyExtractionData = (data: ExtractionResult) => {
        setFieldRows(deriveFieldRowsFromFields(data.fields || {}))
        const pct = data.confidence != null ? ` Confianca: ${(data.confidence * 100).toFixed(0)}%` : ''
        setExtractMessage(`Extracao concluida.${pct}`)
    }

    const runLangExtract = async () => {
        if (!selectedDocumentId || !selectedSchemaId || extracting) return
        setExtracting(true)
        setExtractMessage('Extraindo... isso pode levar alguns segundos.')
        const baseline = {
            resultUpdatedAt: selectedDocument?.extraction_result?.updated_at ?? null,
            metaUpdatedAt:
                (selectedDocument?.metadata as { extraction?: { updated_at?: string } } | undefined)?.extraction
                    ?.updated_at ?? null,
        }
        try {
            const response = await api.post<ExtractionResult>(`/documents/${selectedDocumentId}/langextract`, {
                schema_config_id: selectedSchemaId,
            })
            if (response.status === 202) {
                // Backend queued the LLM extraction (async). Poll the document detail
                // until the new extraction_result lands — or a failure is recorded.
                const outcome = await pollDocumentExtraction(selectedDocumentId, baseline)
                if (outcome.status === 'completed') applyExtractionData(outcome.extraction)
                else if (outcome.status === 'failed') setExtractMessage(`Falha na extracao: ${outcome.error}`)
                else
                    setExtractMessage(
                        'A extracao ainda esta em andamento. Clique em Atualizar em instantes para ver o resultado.',
                    )
            } else {
                // Synchronous response (e.g. local dev). Apply the result directly.
                applyExtractionData(response.data)
            }
        } catch (requestError) {
            setExtractMessage(readError(requestError, 'Falha na extracao LangExtract.'))
        } finally {
            setExtracting(false)
        }
    }

    return {
        fieldRows,
        setFieldRows,
        selectedSchemaId,
        setSelectedSchemaId,
        extracting,
        extractMessage,
        runLangExtract,
    }
}
